import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path
import re

# 1. Definir rutas dinámicas
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "datos_produccion.csv"
SQL_SCRIPT_PATH = BASE_DIR / "sql" / "01_schema_and_queries.sql"

# 2. Configuración de conexión a PostgreSQL
DB_USER = "postgres"
DB_PASS = "casa4512"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "bi_oee_db"

def crear_bd_si_no_existe():
    url_defecto = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/postgres"
    engine_defecto = create_engine(url_defecto, isolation_level="AUTOCOMMIT")
    
    with engine_defecto.connect() as conn:
        resultado = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'"))
        if not resultado.scalar():
            print(f"🛠️ La base de datos '{DB_NAME}' no existe. Creándola automáticamente...")
            conn.execute(text(f'CREATE DATABASE "{DB_NAME}"'))
            print(f"✅ Base de datos '{DB_NAME}' creada con éxito.")

def cargar_datos_postgres():
    print("🚀 Iniciando proceso ETL...")
    
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"❌ No se encontró el archivo CSV en: {DATA_PATH}")

    crear_bd_si_no_existe()

    db_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(db_url)

    # 3. Leer CSV con separador de punto y coma (;) explícito
    try:
        df = pd.read_csv(DATA_PATH, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
    except Exception:
        df = pd.read_csv(DATA_PATH, sep=';', encoding='latin1', on_bad_lines='skip')
    
    # Si por algún motivo se leyó en una sola columna, reintentar con coma (,)
    if len(df.columns) == 1:
        try:
            df = pd.read_csv(DATA_PATH, sep=',', encoding='utf-8-sig', on_bad_lines='skip')
        except Exception:
            df = pd.read_csv(DATA_PATH, sep=',', encoding='latin1', on_bad_lines='skip')

    # 4. Limpieza y estandarización estricta de nombres de columnas
    nuevas_columnas = []
    for col in df.columns:
        c = str(col).lower().strip()
        c = c.replace('ñ', 'ni')
        c = pd.Series(c).str.normalize('NFD').str.encode('ascii', 'ignore').str.decode('utf-8')[0]
        c = re.sub(r'\s+', '_', c)
        c = re.sub(r'[^a-z0-9_]', '', c)
        nuevas_columnas.append(c)
    df.columns = nuevas_columnas

    print(f"📋 Total de columnas procesadas correctamente: {len(df.columns)}")
    print("🔹 Primeras columnas:", df.columns.tolist()[:6])

    # 5. Tratamiento de Data Quality (Limpieza de Nulos)
    if 'codigo_de_paro_1' in df.columns:
        df['codigo_de_paro_1'] = df['codigo_de_paro_1'].fillna('Sin Paro')
    if 'sub_codigo_de_paro_1' in df.columns:
        df['sub_codigo_de_paro_1'] = df['sub_codigo_de_paro_1'].fillna('Sin Paro')

    # Reemplazo de nulos en columnas numéricas clave
    for col_num in ['horas_trabajadas', 'tiempo_de_paro']:
        if col_num in df.columns:
            df[col_num] = pd.to_numeric(df[col_num].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

    # 6. Carga masiva a PostgreSQL
    print(f"📦 Cargando {len(df)} registros en la base de datos PostgreSQL...")
    df.to_sql(
        name='seguimiento_vinilos',
        con=engine,
        schema='public',
        if_exists='replace',
        index=False
    )
    print("✅ Carga masiva completada con éxito en la tabla 'seguimiento_vinilos'.")

    # 7. Ejecución de Vistas SQL
    if SQL_SCRIPT_PATH.exists():
        print("🔧 Creando vistas analíticas en PostgreSQL...")
        with engine.connect() as connection:
            with open(SQL_SCRIPT_PATH, "r", encoding="utf-8") as f:
                sql_script = f.read()
            connection.execute(text(sql_script))
            connection.commit()
        print("🎉 ¡Proceso finalizado! Tu base de datos y vistas están 100% disponibles.")

if __name__ == "__main__":
    cargar_datos_postgres()