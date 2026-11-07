"""Carga a PostgreSQL: staging, dimensiones, hechos y conciliacion."""
import json
import os
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pg8000.dbapi as pg

from etl.transformacion import _texto, seudonimo

RAIZ = Path(__file__).resolve().parent.parent
SQL_DIR = RAIZ / "sql"
SCRIPTS_DDL = ["01_esquemas.sql", "02_staging.sql", "03_dimensiones.sql", "04_hechos.sql", "05_tiempo_real.sql", "06_indices.sql"]


def cargar_env():
    ruta = RAIZ / ".env"
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def conectar(base=None):
    return pg.connect(host=os.environ.get("PGHOST", "localhost"), port=int(os.environ.get("PGPORT", "5432")),
                      user=os.environ.get("PGUSER", "postgres"), password=os.environ.get("PGPASSWORD") or None,
                      database=base or os.environ.get("PGDATABASE", "bi_oee"))


def crear_bd_si_no_existe():
    nombre = os.environ.get("PGDATABASE", "bi_oee")
    con = conectar("postgres")
    con.autocommit = True
    cur = con.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (nombre,))
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE "{nombre}"')
        print(f"base {nombre} creada")
    con.close()


def _valor(v):
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        if np.isnan(v):
            return None
        v = float(v)
        return int(v) if v.is_integer() else v
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, pd.Timestamp):
        return v.date()
    if v is pd.NaT:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def insertar(con, tabla, columnas, filas, chunk=400, sufijo=""):
    cur = con.cursor()
    lista = [tuple(_valor(v) for v in f) for f in filas]
    marcas = "(" + ",".join(["%s"] * len(columnas)) + ")"
    for i in range(0, len(lista), chunk):
        trozo = lista[i:i + chunk]
        sql = f"INSERT INTO {tabla} ({','.join(columnas)}) VALUES " + ",".join([marcas] * len(trozo)) + " " + sufijo
        cur.execute(sql, [v for f in trozo for v in f])


def crear_modelo(con, reset=False):
    cur = con.cursor()
    if reset:
        for esquema in ("rt", "dwh", "stg"):
            cur.execute(f"DROP SCHEMA IF EXISTS {esquema} CASCADE")
    for nombre in SCRIPTS_DDL:
        cur.execute((SQL_DIR / nombre).read_text(encoding="utf-8"))
    con.commit()


def cargar_staging(con, base, sal, archivo, rep):
    d = base.copy()
    d.columns = [c.replace(" ", "_") for c in d.columns]
    num = lambda c: pd.to_numeric(d[c], errors="coerce")
    texto = lambda c: d[c].map(_texto)
    nom = lambda c: texto(c).map(lambda n: seudonimo(n, sal) if isinstance(n, str) and n not in ("No aplica", "No") else None)
    cols = {
        "fila_excel": d["fila_excel"], "fecha": pd.to_datetime(d["Fecha"]).dt.date, "mes": texto("Mes"), "anio": texto("Año"),
        "maquina": texto("Maquina"), "operaria_alias": nom("Operario"), "referencia_origen": texto("Referencia"),
        "pacas": num("Pacas_producidas"), "horas_trabajadas": num("Horas_trabajadas"), "turno_origen": texto("Turno"),
        "horas_no_trabajadas": num("Horas_no_trabajadas"), "tipo_paro_origen": texto("Tipo_de_paro"), "obs_paro": texto("Observaciones_de_paro"),
    }
    for n in range(1, 19):
        cols[f"cod_{n:02d}_min"] = num(f"Codigo_de_paro_{n}")
    cols.update({"subcod_01_origen": texto("Sub_Codigo_de_paro_1"), "subcod_03_origen": texto("Subcodigo_3"), "subcod_05_origen": texto("Subcodigo_5"),
                 "area_subcod_05": texto("Área_involucrada_en_subcodigo_5"), "personal_alias": nom("Personal_involucrado"),
                 "tiempo_paro_h": num("Tiempo_de_Paro"), "observaciones": texto("Observaciones")})
    stg = pd.DataFrame(cols)
    cur = con.cursor()
    cur.execute("TRUNCATE stg.base_datos")
    insertar(con, "stg.base_datos", list(stg.columns), stg.itertuples(index=False, name=None))
    cur.execute("INSERT INTO stg.carga_log (archivo, reporte) VALUES (%s, %s)", (Path(archivo).name, json.dumps(rep, ensure_ascii=False)))
    return len(stg)


def _upsert(con, tabla, columnas, df, conflicto, actualiza):
    sufijo = f"ON CONFLICT ({','.join(conflicto)}) "
    sufijo += ("DO UPDATE SET " + ",".join(f"{c}=EXCLUDED.{c}" for c in actualiza)) if actualiza else "DO NOTHING"
    insertar(con, tabla, columnas, df[columnas].itertuples(index=False, name=None), sufijo=sufijo)


def cargar_dimensiones(con, m):
    cur = con.cursor()
    _upsert(con, "dwh.dim_fecha", list(m["dim_fecha"].columns), m["dim_fecha"], ["fecha_key"], [])
    mq = m["dim_maquina"]
    _upsert(con, "dwh.dim_maquina", list(mq.columns), mq, ["maquina"], ["linea", "unidades_minuto", "factor_meta"])
    tu = m["dim_turno"]
    _upsert(con, "dwh.dim_turno", list(tu.columns), tu, ["turno"], ["tipo_jornada", "hora_inicio", "hora_fin", "horas_nominales", "min_aseo", "min_pausa_activa"])
    pe = m["dim_personal"]
    _upsert(con, "dwh.dim_personal", list(pe.columns), pe, ["alias"], ["rol"])
    pa = m["dim_paro"]
    _upsert(con, "dwh.dim_paro", list(pa.columns), pa, ["codigo", "subcodigo_nivel1", "subcodigo_nivel2"],
            ["nombre_codigo", "area_impacto", "clase_paro", "tipo_perdida_oee"])

    # scd tipo 2 en dim_referencia
    cur.execute("SELECT referencia_key, referencia, marca, tamano_cc, colores, display_por_paca, unidades_por_paca "
                "FROM dwh.dim_referencia WHERE es_vigente AND referencia_key > 0")
    vigentes = {r[1]: r for r in cur.fetchall()}
    nuevas, cambios = [], 0
    hoy = date.today()
    for r in m["dim_referencia"].itertuples(index=False):
        atr = (_valor(r.marca), _valor(r.tamano_cc), _valor(r.colores), _valor(r.display_por_paca), _valor(r.unidades_por_paca))
        actual = vigentes.get(r.referencia)
        if actual is None:
            nuevas.append((r.referencia, *atr, bool(r.en_maestro), r.vigente_desde))
        elif tuple(actual[2:]) != tuple(atr):
            cur.execute("UPDATE dwh.dim_referencia SET vigente_hasta = %s, es_vigente = false WHERE referencia_key = %s", (hoy, actual[0]))
            nuevas.append((r.referencia, *atr, bool(r.en_maestro), hoy))
            cambios += 1
    if nuevas:
        insertar(con, "dwh.dim_referencia", ["referencia", "marca", "tamano_cc", "colores", "display_por_paca", "unidades_por_paca",
                                              "en_maestro", "vigente_desde"], nuevas)
    return cambios


def _mapa(con, sql):
    cur = con.cursor()
    cur.execute(sql)
    return {r[0]: r[1] for r in cur.fetchall()}


def cargar_hechos(con, m):
    cur = con.cursor()
    mq = _mapa(con, "SELECT maquina, maquina_key FROM dwh.dim_maquina")
    tu = _mapa(con, "SELECT turno, turno_key FROM dwh.dim_turno")
    pe = _mapa(con, "SELECT alias, personal_key FROM dwh.dim_personal")
    cur.execute("SELECT referencia, referencia_key, vigente_desde, vigente_hasta FROM dwh.dim_referencia WHERE referencia_key > 0")
    versiones = {}
    for ref, k, d, h in cur.fetchall():
        versiones.setdefault(ref, []).append((d, h, k))
    pk = {}
    cur.execute("SELECT codigo, subcodigo_nivel1, subcodigo_nivel2, paro_key FROM dwh.dim_paro")
    for c, n1, n2, k in cur.fetchall():
        pk[(c, n1, n2)] = k

    def llave_ref(ref, fecha):
        if ref is None or (isinstance(ref, float) and np.isnan(ref)) or ref not in versiones:
            return 0
        for d, h, k in versiones[ref]:
            if d <= fecha <= h:
                return k
        return versiones[ref][-1][2]

    def llave_pers(a):
        return pe.get(a, 0) if isinstance(a, str) else 0

    fp = m["fact_produccion_turno"]
    filas = []
    for r in fp.itertuples(index=False):
        filas.append((r.fila_excel, int(r.fecha.strftime("%Y%m%d")), mq[r.maquina], tu[r.turno], llave_ref(r.referencia, r.fecha),
                      llave_pers(r.operaria), r.tipo_registro, r.horas_programadas, r.pacas_producidas, r.horas_no_trabajadas,
                      r.tipo_no_trabajo_codigo, r.tipo_no_trabajo, round(r.horas_paro_turno, 6), round(r.horas_paro_programado, 6),
                      round(r.horas_paro_calidad, 6), round(r.horas_paro_disponibilidad, 6), round(r.horas_programadas_netas, 6),
                      round(r.horas_operativas, 6), r.meta_pacas_hora, r.pacas_ideales, bool(r.es_atipico), bool(r.sin_referencia), bool(r.meta_estimada), bool(r.incluye_oee)))
    cur.execute("TRUNCATE dwh.fact_produccion_turno, dwh.fact_paro RESTART IDENTITY")
    insertar(con, "dwh.fact_produccion_turno",
             ["fila_excel", "fecha_key", "maquina_key", "turno_key", "referencia_key", "personal_key", "tipo_registro", "horas_programadas",
              "pacas_producidas", "horas_no_trabajadas", "tipo_no_trabajo_codigo", "tipo_no_trabajo", "horas_paro_turno", "horas_paro_programado",
              "horas_paro_calidad", "horas_paro_disponibilidad", "horas_programadas_netas", "horas_operativas", "meta_pacas_hora", "pacas_ideales",
              "es_atipico", "sin_referencia", "meta_estimada", "incluye_oee"], filas)

    ev = m["fact_paro"]
    filas = []
    for r in ev.itertuples(index=False):
        filas.append((r.fila_excel, int(r.fecha.strftime("%Y%m%d")), mq[r.maquina], tu[r.turno], llave_ref(r.referencia, r.fecha),
                      llave_pers(r.operaria), pk[(int(r.codigo), r.subcodigo_nivel1, r.subcodigo_nivel2)], llave_pers(r.personal_involucrado),
                      round(float(r.minutos_paro), 2)))
    insertar(con, "dwh.fact_paro", ["fila_excel", "fecha_key", "maquina_key", "turno_key", "referencia_key", "personal_key", "paro_key",
                                    "personal_involucrado_key", "minutos_paro"], filas)
    return len(fp), len(ev)


def conciliar(con, base, rep):
    """Compara los totales del Excel con los del modelo. La diferencia debe ser igual a lo que se descarto en R2 y R3."""
    n = lambda c: pd.to_numeric(base[c], errors="coerce").fillna(0)
    origen = {"horas_programadas": n("Horas trabajadas").sum(), "pacas": n("Pacas producidas").sum(),
              "horas_no_trabajadas": n("Horas no trabajadas").sum(), "horas_paro": n("Tiempo de Paro").sum()}
    cur = con.cursor()
    cur.execute("SELECT COALESCE(SUM(horas_programadas),0), COALESCE(SUM(pacas_producidas),0), COALESCE(SUM(horas_no_trabajadas),0) FROM dwh.fact_produccion_turno")
    hp, pa, hn = (float(x) for x in cur.fetchone())
    cur.execute("SELECT COALESCE(SUM(horas_paro),0) FROM dwh.fact_paro")
    dp = float(cur.fetchone()[0])
    modelo = {"horas_programadas": hp, "pacas": pa, "horas_no_trabajadas": hn, "horas_paro": dp}
    descartado = rep["descartado"]
    filas = []
    todo_ok = True
    for k in origen:
        dif = origen[k] - modelo[k]
        esperado = descartado.get(k, 0.0)
        ok = bool(abs(dif - esperado) < 0.01)
        todo_ok &= ok
        filas.append({"indicador": k, "excel": round(origen[k], 2), "modelo": round(modelo[k], 2), "diferencia": round(dif, 2),
                      "descartado_en_limpieza": round(esperado, 2), "cuadra": ok})
    return filas, todo_ok
