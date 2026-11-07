"""Punto de entrada del ETL: excel -> staging -> modelo dimensional.

    python etl/run_etl.py            carga completa (se puede repetir)
    python etl/run_etl.py --reset    borra los esquemas y empieza de cero
    python etl/run_etl.py --solo-limpieza   no toca la base de datos
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from etl import carga, extraccion, transformacion  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsm", help="ruta del libro de Excel")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--solo-limpieza", action="store_true")
    args = ap.parse_args()

    carga.cargar_env()
    ruta = Path(args.xlsm or os.environ.get("XLSM_PATH") or RAIZ / "data" / "raw" / "SEGUIMIENTO TEMPERAS Y VINILOS Actividad.xlsm")
    if not ruta.is_absolute():
        ruta = RAIZ / ruta
    if not ruta.exists():
        sys.exit(f"no encuentro el libro de Excel en {ruta}")
    sal = os.environ.get("PSEUDO_SALT", "")
    if not sal:
        print("aviso: PSEUDO_SALT esta vacio, los alias de las personas se calculan sin sal")

    t0 = time.time()
    print("1. leyendo el libro")
    base, catalogos = extraccion.leer_libro(ruta)
    print(f"   {len(base)} filas en la hoja Base De Datos")

    print("2. limpieza")
    df, rep = transformacion.limpiar(base, catalogos, sal)
    modelo, rep = transformacion.construir_modelo(df, catalogos, rep)
    for k in ("R2_duplicados_exactos", "R3_filas_vacias", "R5_pacas_atipicas", "filas_turno_con_produccion",
              "filas_tiempo_sin_programar", "filas_solo_paro", "eventos_de_paro"):
        print(f"   {k}: {rep[k]}")

    if args.solo_limpieza:
        return

    print("3. cargando en PostgreSQL")
    carga.crear_bd_si_no_existe()
    con = carga.conectar()
    try:
        carga.crear_modelo(con, reset=args.reset)
        n_stg = carga.cargar_staging(con, base, sal, ruta, rep)
        cambios = carga.cargar_dimensiones(con, modelo)
        n_prod, n_paro = carga.cargar_hechos(con, modelo)
        filas, ok = carga.conciliar(con, base, rep)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

    print(f"   stg.base_datos: {n_stg} | fact_produccion_turno: {n_prod} | fact_paro: {n_paro} | versiones nuevas de referencias: {cambios}")
    print("4. conciliacion (excel vs modelo)")
    for f in filas:
        print(f"   {f['indicador']:<20} excel={f['excel']:>12,.2f} modelo={f['modelo']:>12,.2f} dif={f['diferencia']:>8,.2f} "
              f"descartado={f['descartado_en_limpieza']:>8,.2f} {'ok' if f['cuadra'] else 'NO CUADRA'}")
    rep["conciliacion"] = filas
    salida = RAIZ / "docs" / "reporte_etl.json"
    salida.parent.mkdir(exist_ok=True)
    salida.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"listo en {time.time() - t0:.0f} s")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
