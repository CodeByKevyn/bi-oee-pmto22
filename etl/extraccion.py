"""Lee el libro de Excel y devuelve DataFrames sin transformar."""
import re
import warnings

import openpyxl
import pandas as pd
from openpyxl.utils import range_boundaries

warnings.filterwarnings("ignore", category=UserWarning)

HOJA_BASE = "Base De Datos"
HOJA_CATALOGOS = "Tablas Desplegables"

# rangos de las tablas del libro (nombre de tabla en Excel -> rango en la hoja)
TABLAS_CATALOGO = {
    "subcodigos_1": "AQ4:AR35",     # Sin_programación
    "subcodigos_3": "AT4:AU9",      # Tabla9
    "subcodigos_5": "AT19:AU30",    # Tabla10
    "paros": "AM4:AO22",            # Tabla2
}
TABLAS_REFERENCIAS = {
    "Vinilos_1": "C124:M178",       # Tabla8
    "Vinilos_2": "C179:M183",       # Tabla14
    "Vinilos_3": "C184:M227",       # Tabla15
    "Vinilos_4": "C228:M262",       # Tabla16
}


def _rango(ws, rango):
    c1, f1, c2, f2 = range_boundaries(rango)
    return list(ws.iter_rows(min_row=f1, max_row=f2, min_col=c1, max_col=c2, values_only=True))


def _limpia_nombre(c, i):
    if c is None:
        return f"col{i}"
    return re.sub(r"\s+", " ", str(c)).strip()


def leer_libro(ruta):
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)

    filas = list(wb[HOJA_BASE].iter_rows(values_only=True))
    h = next(i for i, r in enumerate(filas) if r and r[0] == "Fecha")
    columnas = [_limpia_nombre(c, i) for i, c in enumerate(filas[h])]
    base = pd.DataFrame(filas[h + 1:], columns=columnas)
    base.insert(0, "fila_excel", range(h + 2, h + 2 + len(base)))

    ws = wb[HOJA_CATALOGOS]
    catalogos = {}
    for nombre, rango in TABLAS_CATALOGO.items():
        datos = _rango(ws, rango)
        catalogos[nombre] = pd.DataFrame(datos[1:], columns=[_limpia_nombre(c, i) for i, c in enumerate(datos[0])])

    refs = []
    for maquina, rango in TABLAS_REFERENCIAS.items():
        datos = _rango(ws, rango)
        df = pd.DataFrame(datos[1:], columns=["maquina_fila", "referencia", "colores", "pacas", "display",
                                                 "unidades_paca", "unidades_minuto", "horas", "x1", "x2", "x3"][:len(datos[0])])
        df.insert(0, "maquina", maquina)
        refs.append(df)
    catalogos["referencias"] = pd.concat(refs, ignore_index=True)
    wb.close()
    return base, catalogos
