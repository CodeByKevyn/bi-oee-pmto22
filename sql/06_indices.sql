-- las consultas filtran por fecha y maquina y agrupan por dimensiones: indices sobre las llaves
CREATE INDEX IF NOT EXISTS ix_prod_fecha_maquina ON dwh.fact_produccion_turno (fecha_key, maquina_key);
CREATE INDEX IF NOT EXISTS ix_prod_turno ON dwh.fact_produccion_turno (turno_key);
CREATE INDEX IF NOT EXISTS ix_prod_referencia ON dwh.fact_produccion_turno (referencia_key);
CREATE INDEX IF NOT EXISTS ix_prod_fila ON dwh.fact_produccion_turno (fila_excel);

CREATE INDEX IF NOT EXISTS ix_paro_fecha_maquina ON dwh.fact_paro (fecha_key, maquina_key);
CREATE INDEX IF NOT EXISTS ix_paro_paro ON dwh.fact_paro (paro_key);
CREATE INDEX IF NOT EXISTS ix_paro_turno ON dwh.fact_paro (turno_key);
CREATE INDEX IF NOT EXISTS ix_paro_fila ON dwh.fact_paro (fila_excel);

-- grafana consulta siempre por rango de tiempo y maquina
CREATE INDEX IF NOT EXISTS ix_lectura_ts ON rt.lectura_hora (ts DESC);
CREATE INDEX IF NOT EXISTS ix_lectura_maquina_ts ON rt.lectura_hora (maquina, ts DESC);

-- la dimension de referencias se consulta por nombre y vigencia
CREATE INDEX IF NOT EXISTS ix_dim_ref_nombre ON dwh.dim_referencia (referencia, vigente_desde, vigente_hasta);
