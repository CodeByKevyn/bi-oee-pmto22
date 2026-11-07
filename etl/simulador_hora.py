"""Simula lecturas hora a hora en rt.lectura_hora para probar el tablero y la alerta de Grafana.

    python etl/simulador_hora.py --prefill 24 --segundos-por-hora 5
    python etl/simulador_hora.py --prefill 24 --falla Vinilos_3 --falla-en 6 --falla-horas 5

Cada vuelta del ciclo es una hora simulada de las 4 maquinas. Con --falla una maquina
queda parada varias horas seguidas para ver cuando salta la alerta.
"""
import argparse
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from etl import carga  # noqa: E402

TURNOS = [(6, 14, "Turno 1 (6am-2pm)"), (14, 22, "Turno 2 (2pm-10pm)")]


def turno_de(hora):
    for ini, fin, nombre in TURNOS:
        if ini <= hora < fin:
            return nombre
    return "Turno 3 (10pm-6am)"


def parametros(con):
    """Meta por hora, referencia habitual y pesos de los codigos de paro, tomados de la historia."""
    cur = con.cursor()
    cur.execute("""
        SELECT m.maquina, percentile_cont(0.5) WITHIN GROUP (ORDER BY p.meta_pacas_hora)::float,
               mode() WITHIN GROUP (ORDER BY r.referencia)
        FROM dwh.fact_produccion_turno p
        JOIN dwh.dim_maquina m USING (maquina_key)
        JOIN dwh.dim_referencia r USING (referencia_key)
        WHERE p.incluye_oee
        GROUP BY m.maquina ORDER BY 1""")
    maquinas = {m: {"meta": meta, "referencia": ref} for m, meta, ref in cur.fetchall()}
    cur.execute("""
        SELECT d.codigo, SUM(e.horas_paro)::float
        FROM dwh.fact_paro e JOIN dwh.dim_paro d USING (paro_key) JOIN dwh.dim_fecha f USING (fecha_key)
        WHERE d.clase_paro = 'no programado' AND f.anio >= 2024
        GROUP BY d.codigo""")
    pesos = dict(cur.fetchall())
    cur.execute("""
        SELECT SUM(horas_paro_disponibilidad + horas_paro_calidad) / SUM(horas_programadas_netas) * 60
        FROM dwh.fact_produccion_turno WHERE incluye_oee""")
    min_por_hora = float(cur.fetchone()[0])
    return maquinas, pesos, min_por_hora


def lectura(rng, maquina, datos, pesos, min_por_hora, ts, falla):
    meta = datos["meta"]
    if falla:
        return (ts, maquina, turno_de(ts.hour), datos["referencia"], 0.0, round(meta, 2), round(rng.uniform(55, 60), 1), 1, "falla")
    # un paro en el 55 % de las horas, con duracion media para que el promedio coincida con la historia
    minutos = 0.0
    codigo = None
    if rng.random() < 0.55:
        minutos = min(40.0, rng.expovariate(0.55 / min_por_hora))
        codigo = rng.choices(list(pesos), weights=list(pesos.values()))[0]
    pacas = max(0.0, meta * (1 - minutos / 60.0) * rng.gauss(0.95, 0.05))
    return (ts, maquina, turno_de(ts.hour), datos["referencia"], round(pacas, 2), round(meta, 2), round(minutos, 1), codigo, "normal")


def guardar(con, filas):
    cur = con.cursor()
    carga.insertar(con, "rt.lectura_hora", ["ts", "maquina", "turno", "referencia", "pacas", "meta_pacas", "minutos_paro", "codigo_paro", "escenario"],
                   filas, sufijo="ON CONFLICT (maquina, ts) DO UPDATE SET pacas = EXCLUDED.pacas, meta_pacas = EXCLUDED.meta_pacas, "
                                 "minutos_paro = EXCLUDED.minutos_paro, codigo_paro = EXCLUDED.codigo_paro, escenario = EXCLUDED.escenario, "
                                 "turno = EXCLUDED.turno, referencia = EXCLUDED.referencia")
    con.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefill", type=int, default=24, help="horas de historia que se escriben de una vez")
    ap.add_argument("--segundos-por-hora", type=float, default=5.0)
    ap.add_argument("--horas", type=int, default=0, help="horas simuladas despues del prefill (0 = hasta Ctrl+C)")
    ap.add_argument("--falla", help="maquina que se detiene, por ejemplo Vinilos_3")
    ap.add_argument("--falla-en", type=int, default=6, help="hora (despues del prefill) en que empieza la falla")
    ap.add_argument("--falla-horas", type=int, default=5)
    ap.add_argument("--limpiar", action="store_true", help="vacia rt.lectura_hora antes de empezar")
    ap.add_argument("--semilla", type=int)
    args = ap.parse_args()

    carga.cargar_env()
    rng = random.Random(args.semilla)
    con = carga.conectar()
    maquinas, pesos, min_por_hora = parametros(con)
    if args.limpiar:
        con.cursor().execute("TRUNCATE rt.lectura_hora")
        con.commit()

    inicio = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=args.prefill)
    paso = 0
    print(f"simulando desde {inicio.isoformat()} | maquinas: {', '.join(maquinas)}")
    try:
        while True:
            ts = inicio + timedelta(hours=paso)
            en_vivo = paso >= args.prefill
            h = paso - args.prefill
            filas = []
            for m, datos in maquinas.items():
                falla = bool(args.falla == m and en_vivo and args.falla_en <= h < args.falla_en + args.falla_horas)
                filas.append(lectura(rng, m, datos, pesos, min_por_hora, ts, falla))
            guardar(con, filas)
            if en_vivo:
                resumen = ", ".join(f"{f[1][-1]}: {f[6]:.0f} min" for f in filas)
                print(f"{ts:%Y-%m-%d %H:00} (hora {h}) paro -> {resumen}")
                if args.horas and h + 1 >= args.horas:
                    break
                time.sleep(args.segundos_por_hora)
            paso += 1
    except KeyboardInterrupt:
        print("detenido")
    finally:
        con.close()


if __name__ == "__main__":
    main()
