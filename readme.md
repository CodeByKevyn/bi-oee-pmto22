# BI OEE & Análisis de Paros (P-MTO-22)

Pipeline ETL automatizado y sistema de Inteligencia de Negocios para el monitoreo del OEE (Efectividad Global de Equipos) y el análisis de paros en planta bajo el estándar **P-MTO-22**.

---

## 📌 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado en tu equipo:

- **[Git](https://git-scm.com/)**
- **[Python 3.10+](https://www.python.org/)**
- **[PostgreSQL 14+](https://www.postgresql.org/)** (Servidor activo en `localhost:5432`).
- **[Visual Studio Code](https://code.visualstudio.com/)**

---

## 📂 Estructura del Proyecto

```text
bi-oee-pmto22/
├── data/
│   └── datos_produccion.csv        # Dataset original (8,208 registros, 58 columnas)
├── scripts/
│   └── etl_load.py                 # Pipeline ETL automatizado en Python
├── sql/
│   └── 01_schema_and_queries.sql   # Vistas analíticas (vw_oee_resumen_maquina, vw_pareto_paros)
├── powerbi/
│   └── bi-oee-pmto22-powerbi.pbix  # Informe interactivo en Power BI
├── .gitignore
└── README.md
```

---

## 🚀 Guía Paso a Paso: Instalación y Ejecución

### 1. Clonar el Repositorio

Abre la terminal de tu sistema o la terminal integrada de VS Code (`Ctrl + ~`) y ejecuta los siguientes comandos:

**PowerShell:**

```powershell
git clone https://github.com/TU_USUARIO/bi-oee-pmto22.git
cd bi-oee-pmto22
```

### 2. Instalar Dependencias de Python

Instala las librerías necesarias para ejecutar el pipeline de datos:

**PowerShell:**

```powershell
pip install pandas sqlalchemy psycopg2-binary
```

### 3. Configurar Credenciales de PostgreSQL

Abre el archivo `scripts/etl_load.py` en VS Code y ajusta las variables de conexión con tu contraseña local de PostgreSQL (líneas 13-17):

**Python:**

```python
DB_USER = "postgres"
DB_PASS = "tu_contraseña_aqui"  # Sustituir por tu contraseña de PostgreSQL
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "bi_oee_db"
```

### 4. Ejecutar el Pipeline ETL Automatizado

Ejecuta el siguiente comando desde la terminal:

**PowerShell:**

```powershell
python scripts/etl_load.py
```

**Acciones automatizadas por el script:**

1. Crea automáticamente la base de datos `bi_oee_db` en PostgreSQL si no existe.
2. Lee el archivo `data/datos_produccion.csv`, autodetectando el delimitador (`;`) y corrigiendo codificaciones UTF-8/Latin1.
3. Normaliza las 58 columnas (remueve tildes, espacios y caracteres especiales).
4. Aplica tratamiento de calidad de datos (*Data Quality*), completando valores nulos en códigos de paro y variables numéricas.
5. Realiza la carga masiva de los 8,208 registros en la tabla `public.seguimiento_vinilos`.
6. Ejecuta el archivo `sql/01_schema_and_queries.sql` para generar las vistas analíticas necesarias.

---

## 🔍 Verificación en PostgreSQL (pgAdmin 4)

1. Abre **pgAdmin 4**.
2. En el panel izquierdo (*Object Explorer*), haz clic derecho sobre **Databases** y selecciona **Refresh**.
3. Despliega la siguiente ruta:

```text
Databases
└── bi_oee_db
    └── Schemas
        └── public
```

4. Confirma la creación de los siguientes objetos:

   - **Tables:** `seguimiento_vinilos`
   - **Views:** `vw_oee_resumen_maquina` y `vw_pareto_paros`

Para consultar la disponibilidad por máquina desde el **Query Tool**, ejecuta:

**SQL:**

```sql
SELECT *
FROM public.vw_oee_resumen_maquina;
```

---

## 📊 Integración con Visualizadores (Grafana / Power BI)

### Conexión en Grafana

1. Abre Grafana desde el navegador: [http://localhost:3000](http://localhost:3000).
2. Dirígete a **Connections → Data Sources → Add data source**.
3. Selecciona **PostgreSQL**.
4. Diligencia las credenciales de conexión:

   - **Host:** `localhost:5432`
   - **Database:** `bi_oee_db`
   - **SSL Mode:** `disable`

5. Consulta las vistas directamente desde los paneles SQL:

**SQL:**

```sql
SELECT maquina, disponibilidad_pct
FROM vw_oee_resumen_maquina;
```

### Conexión en Power BI

1. Abre el archivo `powerbi/bi-oee-pmto22-powerbi.pbix` en **Power BI Desktop**.
2. Dirígete a **Inicio → Transformar datos → Configuración de origen de datos**.
3. Actualiza el servidor de origen a `localhost` y selecciona la base de datos `bi_oee_db`.