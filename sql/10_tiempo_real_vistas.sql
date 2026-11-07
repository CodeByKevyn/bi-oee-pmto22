CREATE OR REPLACE VIEW dwh.v_codigos AS
SELECT DISTINCT codigo, nombre_codigo, area_impacto, clase_paro, tipo_perdida_oee
FROM dwh.dim_paro;

-- ultima lectura de cada maquina y su estado
CREATE OR REPLACE VIEW rt.v_estado_actual AS
SELECT DISTINCT ON (l.maquina)
       l.maquina, l.ts, l.turno, l.pacas, l.meta_pacas,
       ROUND(100 * l.pacas / NULLIF(l.meta_pacas, 0), 1) AS cumplimiento_pct,
       l.minutos_paro, l.codigo_paro, c.nombre_codigo,
       CASE WHEN l.minutos_paro >= 45 THEN 'Parada'
            WHEN l.minutos_paro >= 15 THEN 'Con paros'
            ELSE 'Produciendo' END AS estado
FROM rt.lectura_hora l
LEFT JOIN dwh.v_codigos c ON c.codigo = l.codigo_paro
ORDER BY l.maquina, l.ts DESC;

-- ventana de las ultimas 3 lecturas (horas) de cada maquina; es la que mira la alerta
CREATE OR REPLACE VIEW rt.v_ultimas_3h AS
SELECT maquina,
       COUNT(*) AS horas,
       SUM(minutos_paro) AS minutos_paro,
       ROUND(100 * SUM(minutos_paro) / (60.0 * COUNT(*)), 1) AS paro_pct,
       ROUND(100 * SUM(pacas) / NULLIF(SUM(meta_pacas), 0), 1) AS cumplimiento_pct,
       MAX(ts) AS ultima_lectura
FROM (SELECT l.*, ROW_NUMBER() OVER (PARTITION BY maquina ORDER BY ts DESC) AS n FROM rt.lectura_hora l) x
WHERE n <= 3
GROUP BY maquina;
