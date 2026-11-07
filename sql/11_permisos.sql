-- las herramientas de BI se conectan con un usuario que pertenece a bi_lectura: ve dwh y rt, no ve stg
GRANT USAGE ON SCHEMA dwh, rt TO bi_lectura;
GRANT SELECT ON ALL TABLES IN SCHEMA dwh TO bi_lectura;
GRANT SELECT ON ALL TABLES IN SCHEMA rt TO bi_lectura;
REVOKE ALL ON SCHEMA stg FROM bi_lectura;
