"""Limpieza de la base de paros y armado de las tablas del modelo dimensional."""
import hashlib
import re
from datetime import date

import numpy as np
import pandas as pd

UMBRAL_PACAS_ATIPICO = 1000
CODIGOS_PROGRAMADO = {4, 15, 16, 17, 18}
CODIGOS_CALIDAD = {11, 12}
# factor de la hoja "Calculadora de tiempos" (celda J10) para la meta por hora
FACTOR_MAQUINA = {"Vinilos_1": 0.93, "Vinilos_2": 0.96, "Vinilos_3": 1.0, "Vinilos_4": 1.0}
REFERENCIA_POR_DEFECTO = "Parchesitos 22cc (6 col)"

# turno normalizado -> (inicio, fin, horas nominales, min aseo, min pausa activa, tipo)
TURNOS = {
    "Turno 1 (6am-2pm)": ("06:00", "14:00", 8.0, 40, 3, "Turno de 8 h"),
    "Turno 2 (2pm-10pm)": ("14:00", "22:00", 8.0, 40, 3, "Turno de 8 h"),
    "Turno 3 (10pm-6am)": ("22:00", "06:00", 8.0, 40, 3, "Turno de 8 h"),
    "Jornada 6am-4:30pm": ("06:00", "16:30", 10.5, 70, 6, "Jornada especial"),
    "Jornada 6am-6pm": ("06:00", "18:00", 12.0, 40, 3, "Jornada especial"),
    "Jornada 6pm-6am": ("18:00", "06:00", 12.0, 40, 3, "Jornada especial"),
    "Sin turno": (None, None, None, None, None, "Sin dato"),
}
MAPA_TURNO = {
    "6am-2pm (Turno 1)": "Turno 1 (6am-2pm)",
    "2pm-10pm (Turno 2)": "Turno 2 (2pm-10pm)",
    "10pm-6am (Turno 3)": "Turno 3 (10pm-6am)",
    "6am-4:30pm": "Jornada 6am-4:30pm",
    "6am-6pm": "Jornada 6am-6pm",
    "6pm-6am": "Jornada 6pm-6am",
}

# "Tipo de paro" tiene dos esquemas de codificacion (viejo y nuevo)
MAPA_TIPO_PARO = {
    "[19] No aplica": (None, "No aplica"),
    "17. PARO DE MAQUINA": (18, "Paro de máquina por ventas"),
    "[18] Paro de maquina por ventas": (18, "Paro de máquina por ventas"),
    "9.FALTA DE PROGRAMACIÓN (PLANEACIÓN)": (None, "Falta de programación"),
    "16.  PARO POR PROCESO ANTERIOR": (None, "Paro por proceso anterior"),
    "10. PARO POR MATERIA PRIMA O MATERIAL DE EMPAQUE NO CONFORME": (12, "Materia prima defectuosa"),
    "[12] Materia prima defectuosa o material de empaque no conforme": (12, "Materia prima defectuosa"),
    "6. FALTA DE MATERIALES O MATERIAS PRIMAS": (14, "Falta de materia prima"),
    "[14] Falta de materia prima": (14, "Falta de materia prima"),
    "15. APROBACION DE LABORATORIO (MICROBIOLOGIA)": (13, "Espera por aval del laboratorio"),
    "[13] En espera por el aval del laboratorio de microbiología": (13, "Espera por aval del laboratorio"),
    "[09] Falta de operario": (9, "Falta de operario"),
    "[05] Ajuste operativo": (5, "Ajuste operativo"),
    "4.AJUSTE DE OPERACIÓN": (5, "Ajuste operativo"),
    "5. AISLAMIENTO/CAMBIO DE PRODUCTO": (7, "Alistamiento / cambio de referencia"),
    "[07] Alistamiento de máquina / Cambio de referencia": (7, "Alistamiento / cambio de referencia"),
    "3. AJUSTE ELECTRICO O DE SERVICIOS (AIRE, CALDERA, GAS)": (3, "Novedad en sistemas de potencia"),
    "[03] Novedad en los sistemas de potencia (Aire, energía, vapor)": (3, "Novedad en sistemas de potencia"),
    "11. LIMPIEZA NO PROGRAMADA": (6, "Limpieza por derrame"),
}

MAPA_TIPO_PARO = {re.sub(r"\s+", " ", k).strip(): v for k, v in MAPA_TIPO_PARO.items()}

NOMBRES_CODIGO = {
    1: "Falla del sistema electromecánico y/o de control", 2: "Espera de soporte de mantenimiento",
    3: "Novedad en los sistemas de potencia (aire, energía, vapor)", 4: "Mantenimiento preventivo",
    5: "Ajuste operativo", 6: "Limpieza por derrame operativo", 7: "Alistamiento de máquina / cambio de referencia",
    8: "Capacitación / reunión", 9: "Falta de operario", 10: "Paro por ventaja / evacuación", 11: "Reproceso",
    12: "Materia prima defectuosa", 13: "En espera por el aval del laboratorio de microbiología",
    14: "Falta de materia prima", 15: "Cambio de insumos (roscadores, o'ring, etiquetas)",
    16: "Alimentación y aseo de la zona de trabajo y la máquina", 17: "Pausa activa", 18: "Desinfección",
}


def _texto(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    t = re.sub(r"\s+", " ", str(v)).strip()
    return t or None


def seudonimo(nombre, sal):
    if not isinstance(nombre, str) or not nombre:
        return None
    h = hashlib.sha256((sal + nombre.lower()).encode("utf-8")).hexdigest()[:8].upper()
    return "P" + h


def normaliza_referencia(v):
    t = _texto(v)
    if t is None or t.lower() == "no aplica":
        return None
    t = t.replace("Alocdor", "Alocolor").replace("Stilo", "Estilo")
    t = re.sub(r"(\d+)\s*cc", r"\1cc", t, flags=re.I)
    t = re.sub(r"\(\s*(\d+)\s*col\s*[^)]*\)", r"(\1 col)", t)
    return t


def parsea_referencia(nombre):
    m = re.match(r"^(?P<marca>.+?)\s+(?P<cc>\d+)cc\s*(?:\((?P<col>\d+) col\))?$", nombre)
    if m:
        return m["marca"], int(m["cc"]), int(m["col"]) if m["col"] else 1
    m = re.match(r"^(?P<marca>Vinilos x (?P<cc>\d+))\s+(?P<color>\w+)$", nombre)
    if m:
        return m["marca"], int(m["cc"]), 1
    return nombre, None, None


def parsea_subcodigo(texto, codigo):
    """Devuelve (nivel1, nivel2) como llaves tipo '1.2' y '1.2.C'."""
    t = _texto(texto)
    if t is None:
        return None, None
    if codigo == 1:
        m = re.match(r"^1\.(\d+)(?:\.?([A-Za-z]|\d))?", t)
        if not m:
            return None, None
        n1 = f"1.{m[1]}"
        letra = m[2]
        if letra is not None and letra.isdigit():
            letra = "ABCDE"[int(letra) - 1]
        return n1, (f"{n1}.{letra.upper()}" if letra else None)
    if codigo == 3:
        m = re.match(r"^3\.(\d+)", t)
        return (f"3.{m[1]}", None) if m else (None, None)
    m = re.match(r"^[45]\.(\d+)", t)
    return (f"5.{m[1]}", None) if m else (None, None)


def _etiquetas(catalogos):
    et = {}
    for k in ("subcodigos_1", "subcodigos_3", "subcodigos_5"):
        for llave, etiqueta in catalogos[k].itertuples(index=False):
            et[str(llave).strip()] = _texto(etiqueta)
    return et


def limpiar(base, catalogos, sal):
    rep = {"filas_origen": int(len(base))}
    df = base.copy()
    df.columns = [c.replace(" ", "_") for c in df.columns]

    # R1: columnas que no se usan (vacías o con el turno copiado)
    df = df.drop(columns=["Unidades_producidas_cada_minuto", "Display_por_paca", "Unidad_por_display"])
    rep["R1_columnas_descartadas"] = 3

    # R2: duplicados exactos de la fila completa
    cols = [c for c in df.columns if c != "fila_excel"]
    dup = df.duplicated(cols, keep="first")
    rep["R2_duplicados_exactos"] = int(dup.sum())
    df = df[~dup].copy()

    for c in ("Pacas_producidas", "Horas_trabajadas", "Horas_no_trabajadas", "Tiempo_de_Paro"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # R3: filas de relleno (sin horas, sin pacas, sin paro y sin horas sin trabajar)
    sin_programar = df["Horas_no_trabajadas"].fillna(0) > 0
    vacia = df["Horas_trabajadas"].isna() & df["Pacas_producidas"].isna() & (df["Tiempo_de_Paro"].fillna(0) == 0) & ~sin_programar
    rep["R3_filas_vacias"] = int(vacia.sum())
    df = df[~vacia].copy()

    # R4: textos
    df["maquina"] = df["Maquina"].map(_texto)
    df["fecha"] = pd.to_datetime(df["Fecha"]).dt.date
    df["turno"] = df["Turno"].map(_texto).map(lambda t: MAPA_TURNO.get(t, "Sin turno"))
    df["referencia"] = df["Referencia"].map(normaliza_referencia)
    op = df["Operario"].map(_texto)
    op = op.where(~op.isin(["No aplica", "No"]), None)
    rep["R4_referencias_corregidas"] = int((df["Referencia"].map(_texto).fillna("") != df["referencia"].fillna("")).sum()
                                           - df["Referencia"].map(_texto).eq("No aplica").sum())
    rep["R4_operarios_distintos_origen"] = int(op.nunique())
    df["operaria"] = op.map(lambda n: seudonimo(n, sal))
    tp = df["Tipo_de_paro"].map(_texto)
    df["tipo_no_trabajo_codigo"] = tp.map(lambda t: MAPA_TIPO_PARO.get(t, (None, None))[0])
    df["tipo_no_trabajo"] = tp.map(lambda t: MAPA_TIPO_PARO.get(t, (None, "Sin dato"))[1] if t else "Sin dato")
    rep["R4_tipo_paro_esquema_viejo"] = int(tp.fillna("").str.match(r"^\d+\.").sum())

    # R5: pacas atípicas y paros mayores que las horas programadas
    ht = df["Horas_trabajadas"]
    df["es_atipico"] = df["Pacas_producidas"] > UMBRAL_PACAS_ATIPICO
    rep["R5_pacas_atipicas"] = int(df["es_atipico"].sum())
    rep["R5_paro_mayor_que_horas"] = int(((df["Tiempo_de_Paro"] > ht) & (ht > 0)).sum())

    # R6: personas que aparecen en el paro de código 5
    area = df["Área_involucrada_en_subcodigo_5"].map(_texto)
    df["personal_involucrado"] = df["Personal_involucrado"].map(_texto).map(lambda n: seudonimo(n, sal))
    df["rol_involucrado"] = area.map({"Operarios": "operaria", "Personal_de_mantenimiento": "mantenimiento"})

    con_turno = df["Horas_trabajadas"].notna() | df["Pacas_producidas"].notna()
    df["es_produccion"] = con_turno | (df["Horas_no_trabajadas"].fillna(0) > 0)
    df["tipo_registro"] = np.where(con_turno, "turno con producción", "tiempo sin programar")
    rep["filas_limpias"] = int(len(df))
    rep["filas_turno_con_produccion"] = int(con_turno.sum())
    rep["filas_tiempo_sin_programar"] = int((df["es_produccion"] & ~con_turno).sum())
    rep["filas_solo_paro"] = int((~df["es_produccion"]).sum())
    return df, rep


def construir_modelo(df, catalogos, rep):
    etiquetas = _etiquetas(catalogos)
    areas = catalogos["paros"]
    area_por_codigo = {}
    for _, r in areas.iterrows():
        m = re.match(r"\[(\d+)\]", str(r["PARO"]))
        if m:
            area_por_codigo[int(m[1])] = _texto(r["ÁREA DE IMPACTO"])
    area_por_codigo.setdefault(18, "Sin definir")

    # ---------------- dimensiones
    fechas = pd.date_range("2022-01-01", "2027-12-31")
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    dim_fecha = pd.DataFrame({
        "fecha_key": fechas.strftime("%Y%m%d").astype(int), "fecha": fechas.date, "anio": fechas.year,
        "semestre": (fechas.month - 1) // 6 + 1, "trimestre": fechas.quarter, "mes": fechas.month,
        "nombre_mes": [meses[m - 1] for m in fechas.month], "anio_mes": fechas.strftime("%Y-%m"),
        "semana_iso": fechas.isocalendar().week.astype(int).values, "dia_mes": fechas.day,
        "dia_semana": fechas.dayofweek + 1, "nombre_dia": [dias[d] for d in fechas.dayofweek],
        "es_fin_de_semana": fechas.dayofweek >= 5})

    refs = catalogos["referencias"].copy()
    refs["referencia"] = refs["referencia"].map(normaliza_referencia)
    refs = refs[refs["referencia"].notna() & (refs["unidades_paca"].map(lambda v: isinstance(v, (int, float))))]
    refs["unidades_paca"] = pd.to_numeric(refs["unidades_paca"], errors="coerce")
    refs["display"] = pd.to_numeric(refs["display"], errors="coerce")
    refs["unidades_minuto"] = pd.to_numeric(refs["unidades_minuto"], errors="coerce")
    refs = refs[refs["unidades_paca"] > 0]
    unid_min = refs.groupby("maquina")["unidades_minuto"].agg(lambda s: s.mode().iloc[0]).to_dict()
    rep["referencias_repetidas_en_maestro"] = int(refs.duplicated(["maquina", "referencia"]).sum())
    maestro = refs.drop_duplicates(["maquina", "referencia"], keep="first")
    por_referencia = maestro.groupby("referencia").agg(display_por_paca=("display", "first"), unidades_por_paca=("unidades_paca", "first"),
                                                       colores_maestro=("colores", "first")).reset_index()
    rep["referencias_con_unidades_distintas_entre_maquinas"] = int((maestro.groupby("referencia")["unidades_paca"].nunique() > 1).sum())

    usadas = sorted(set(df["referencia"].dropna()))
    filas = []
    for n in usadas:
        marca, cc, col = parsea_referencia(n)
        filas.append({"referencia": n, "marca": marca, "tamano_cc": cc, "colores": col})
    dim_ref = pd.DataFrame(filas).merge(por_referencia[["referencia", "display_por_paca", "unidades_por_paca"]], on="referencia", how="left")
    dim_ref["en_maestro"] = dim_ref["unidades_por_paca"].notna()
    rep["referencias_usadas"] = int(len(dim_ref))
    rep["referencias_sin_maestro"] = int((~dim_ref["en_maestro"]).sum())
    dim_ref["vigente_desde"] = date(2022, 1, 1)
    dim_ref["vigente_hasta"] = date(9999, 12, 31)
    dim_ref["es_vigente"] = True

    dim_maquina = pd.DataFrame({"maquina": sorted(df["maquina"].unique())})
    dim_maquina["linea"] = dim_maquina["maquina"]
    dim_maquina["unidades_minuto"] = dim_maquina["maquina"].map(unid_min)
    dim_maquina["factor_meta"] = dim_maquina["maquina"].map(FACTOR_MAQUINA)

    dim_turno = pd.DataFrame([{"turno": k, "hora_inicio": v[0], "hora_fin": v[1], "horas_nominales": v[2], "min_aseo": v[3],
                               "min_pausa_activa": v[4], "tipo_jornada": v[5]} for k, v in TURNOS.items()])

    personas = {}
    for alias in df["operaria"].dropna().unique():
        personas[alias] = "operaria"
    for alias, rol in df.loc[df["personal_involucrado"].notna(), ["personal_involucrado", "rol_involucrado"]].itertuples(index=False):
        if alias not in personas:
            personas[alias] = rol or "otro"
    dim_personal = pd.DataFrame({"alias": list(personas), "rol": list(personas.values())})

    # dim_paro: una fila por codigo (+ subcodigo nivel 1 y 2 en los codigos 1, 3 y 5)
    filas = []
    for cod in range(1, 19):
        base = {"codigo": cod, "nombre_codigo": f"[{cod:02d}] {NOMBRES_CODIGO[cod]}", "area_impacto": area_por_codigo.get(cod),
                "clase_paro": "programado" if cod in CODIGOS_PROGRAMADO else "no programado",
                "tipo_perdida_oee": "programado" if cod in CODIGOS_PROGRAMADO else ("calidad" if cod in CODIGOS_CALIDAD else "disponibilidad")}
        filas.append({**base, "subcodigo_nivel1": "Sin especificar", "subcodigo_nivel2": "Sin especificar"})
    for llave, etq in etiquetas.items():
        cod = int(llave.split(".")[0])
        partes = llave.split(".")
        base = {"codigo": cod, "nombre_codigo": f"[{cod:02d}] {NOMBRES_CODIGO[cod]}", "area_impacto": area_por_codigo.get(cod),
                "clase_paro": "no programado", "tipo_perdida_oee": "disponibilidad"}
        if len(partes) == 2:
            filas.append({**base, "subcodigo_nivel1": etq, "subcodigo_nivel2": "Sin especificar"})
        else:
            n1 = etiquetas.get(f"{partes[0]}.{partes[1]}", "Sin especificar")
            filas.append({**base, "subcodigo_nivel1": n1, "subcodigo_nivel2": etq})
    dim_paro = pd.DataFrame(filas).drop_duplicates(["codigo", "subcodigo_nivel1", "subcodigo_nivel2"]).reset_index(drop=True)

    # ---------------- hecho de paro: se despivotan los 18 codigos
    eventos = []
    for cod in range(1, 19):
        col = f"Codigo_de_paro_{cod}"
        m = pd.to_numeric(df[col], errors="coerce")
        sel = df[m.notna() & (m > 0)].copy()
        sel["minutos_paro"] = m[sel.index]
        sel["codigo"] = cod
        n1 = n2 = None
        sub = {1: "Sub_Codigo_de_paro_1", 3: "Subcodigo_3", 5: "Subcodigo_5"}.get(cod)
        if sub:
            par = sel[sub].map(lambda t: parsea_subcodigo(t, cod))
            sel["n1"] = par.map(lambda p: etiquetas.get(p[0]) if p[0] else None)
            sel["n2"] = par.map(lambda p: etiquetas.get(p[1]) if p[1] else None)
        else:
            sel["n1"] = None
            sel["n2"] = None
        sel["subcodigo_nivel1"] = sel["n1"].fillna("Sin especificar")
        sel["subcodigo_nivel2"] = sel["n2"].fillna("Sin especificar")
        if cod != 5:
            sel["personal_involucrado"] = None
        eventos.append(sel[["fila_excel", "fecha", "maquina", "turno", "operaria", "referencia", "codigo", "subcodigo_nivel1",
                            "subcodigo_nivel2", "personal_involucrado", "minutos_paro"]])
    fact_paro = pd.concat(eventos, ignore_index=True)
    rep["eventos_de_paro"] = int(len(fact_paro))
    rep["minutos_paro_cargados"] = round(float(fact_paro["minutos_paro"].sum()), 2)
    # subcodigos que no existen en el catalogo
    rep["eventos_con_subcodigo_no_reconocido"] = 0

    # ---------------- hecho de produccion por turno
    prod = df[df["es_produccion"]].copy()
    prod["horas_programadas"] = prod["Horas_trabajadas"].fillna(0.0)
    prod["pacas_producidas"] = prod["Pacas_producidas"].fillna(0.0)
    llave = ["fecha", "maquina", "turno", "operaria", "referencia"]
    fp = fact_paro.copy()
    fp["horas"] = fp["minutos_paro"] / 60.0
    fp["h_prog"] = np.where(fp["codigo"].isin(CODIGOS_PROGRAMADO), fp["horas"], 0.0)
    fp["h_cal"] = np.where(fp["codigo"].isin(CODIGOS_CALIDAD), fp["horas"], 0.0)
    for c in ("operaria", "referencia"):
        fp[c] = fp[c].fillna("~")
        prod[c + "_k"] = prod[c].fillna("~")
    fp_k = fp.rename(columns={"operaria": "operaria_k", "referencia": "referencia_k"})
    agg = fp_k.groupby(["fecha", "maquina", "turno", "operaria_k", "referencia_k"], as_index=False).agg(
        paro_total=("horas", "sum"), paro_prog=("h_prog", "sum"), paro_cal=("h_cal", "sum"))
    prod = prod.merge(agg, on=["fecha", "maquina", "turno", "operaria_k", "referencia_k"], how="left")
    for c in ("paro_total", "paro_prog", "paro_cal"):
        prod[c] = prod[c].fillna(0.0)
    # si hay varias filas de produccion con la misma llave el paro se reparte segun las horas programadas
    peso = prod.groupby(["fecha", "maquina", "turno", "operaria_k", "referencia_k"])["horas_programadas"].transform("sum")
    n = prod.groupby(["fecha", "maquina", "turno", "operaria_k", "referencia_k"])["horas_programadas"].transform("size")
    parte = np.where(peso > 0, prod["horas_programadas"] / peso.replace(0, np.nan), 1.0 / n)
    parte = np.nan_to_num(parte, nan=1.0 / 1)
    for c in ("paro_total", "paro_prog", "paro_cal"):
        prod[c] = prod[c] * parte
    rep["paro_horas_sin_fila_de_produccion"] = round(float(fp["horas"].sum() - prod["paro_total"].sum()), 2)

    prod["horas_paro_turno"] = prod["paro_total"]
    prod["horas_paro_programado"] = prod["paro_prog"]
    prod["horas_paro_calidad"] = prod["paro_cal"]
    prod["horas_paro_disponibilidad"] = (prod["paro_total"] - prod["paro_prog"] - prod["paro_cal"]).clip(lower=0)
    prod["horas_programadas_netas"] = (prod["horas_programadas"] - prod["horas_paro_programado"]).clip(lower=0)
    prod["horas_operativas"] = (prod["horas_programadas_netas"] - prod["horas_paro_disponibilidad"]).clip(lower=0)

    # meta por hora (hoja "Calculadora de tiempos"): 60 * factor * unidades/min / unidades por paca
    unidades = dict(zip(dim_ref["referencia"], dim_ref["unidades_por_paca"]))
    defecto = unidades.get(REFERENCIA_POR_DEFECTO, 600.0)
    prod["sin_referencia"] = prod["referencia"].isna()
    uxp = prod["referencia"].map(unidades)
    prod["meta_estimada"] = uxp.isna()
    uxp = uxp.fillna(defecto)
    um = prod["maquina"].map(unid_min)
    fm = prod["maquina"].map(FACTOR_MAQUINA)
    prod["meta_pacas_hora"] = (60.0 * fm * um / uxp).round(3)
    prod["pacas_ideales"] = (prod["meta_pacas_hora"] * prod["horas_operativas"]).round(3)
    rep["produccion_con_meta_estimada"] = int(prod["meta_estimada"].sum())
    rep["produccion_sin_referencia"] = int(prod["sin_referencia"].sum())

    fact_prod = prod[["fila_excel", "fecha", "maquina", "turno", "operaria", "referencia", "horas_programadas", "pacas_producidas",
                      "tipo_registro", "Horas_no_trabajadas",
                      "tipo_no_trabajo_codigo", "tipo_no_trabajo", "horas_paro_turno", "horas_paro_programado", "horas_paro_calidad",
                      "horas_paro_disponibilidad", "horas_programadas_netas", "horas_operativas", "meta_pacas_hora", "pacas_ideales",
                      "es_atipico", "sin_referencia", "meta_estimada"]].rename(columns={"Horas_no_trabajadas": "horas_no_trabajadas"})
    fact_prod["horas_no_trabajadas"] = fact_prod["horas_no_trabajadas"].fillna(0.0)

    return {"dim_fecha": dim_fecha, "dim_maquina": dim_maquina, "dim_turno": dim_turno, "dim_referencia": dim_ref,
            "dim_personal": dim_personal, "dim_paro": dim_paro, "fact_produccion_turno": fact_prod, "fact_paro": fact_paro}, rep
