CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS dwh;
CREATE SCHEMA IF NOT EXISTS rt;

COMMENT ON SCHEMA stg IS 'Copia de la hoja Base De Datos con alias en lugar de nombres. Solo la usa el ETL.';
COMMENT ON SCHEMA dwh IS 'Modelo dimensional para Power BI y consultas analiticas.';
COMMENT ON SCHEMA rt IS 'Lecturas hora a hora (simuladas) para Grafana.';

-- rol de solo lectura para las herramientas de BI (no ve stg)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bi_lectura') THEN
        CREATE ROLE bi_lectura NOLOGIN;
    END IF;
END $$;
