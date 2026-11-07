-- indicadores por maquina y mes
-- productividad = la misma formula del P-MTO-22: (horas programadas - horas de paro) / horas programadas
-- el OEE solo usa filas con referencia conocida y sin valores atipicos (incluye_oee)
CREATE OR REPLACE VIEW dwh.v_kpi_maquina_mes AS
WITH prod AS (
    SELECT f.anio, f.mes, f.anio_mes, p.maquina_key,
           SUM(p.horas_programadas) AS horas_programadas,
           SUM(p.pacas_producidas) AS pacas,
           SUM(p.horas_no_trabajadas) AS horas_no_trabajadas,
           SUM(p.horas_programadas_netas) FILTER (WHERE p.incluye_oee) AS oee_horas_netas,
           SUM(p.horas_operativas) FILTER (WHERE p.incluye_oee) AS oee_horas_operativas,
           SUM(p.horas_paro_calidad) FILTER (WHERE p.incluye_oee) AS oee_horas_calidad,
           SUM(p.pacas_producidas) FILTER (WHERE p.incluye_oee) AS oee_pacas,
           SUM(p.pacas_ideales) FILTER (WHERE p.incluye_oee) AS oee_pacas_ideales
    FROM dwh.fact_produccion_turno p
    JOIN dwh.dim_fecha f USING (fecha_key)
    GROUP BY f.anio, f.mes, f.anio_mes, p.maquina_key
), paro AS (
    SELECT f.anio_mes, e.maquina_key, SUM(e.horas_paro) AS horas_paro
    FROM dwh.fact_paro e
    JOIN dwh.dim_fecha f USING (fecha_key)
    GROUP BY f.anio_mes, e.maquina_key
)
SELECT prod.anio, prod.mes, prod.anio_mes, m.maquina,
       prod.horas_programadas,
       COALESCE(paro.horas_paro, 0) AS horas_paro,
       prod.pacas,
       prod.horas_no_trabajadas,
       ROUND((prod.horas_programadas - COALESCE(paro.horas_paro, 0)) / NULLIF(prod.horas_programadas, 0), 4) AS productividad_pmto22,
       ROUND(prod.oee_horas_operativas / NULLIF(prod.oee_horas_netas, 0), 4) AS disponibilidad,
       ROUND(prod.oee_pacas / NULLIF(prod.oee_pacas_ideales, 0), 4) AS rendimiento,
       ROUND(1 - prod.oee_horas_calidad / NULLIF(prod.oee_horas_operativas, 0), 4) AS calidad,
       ROUND(prod.oee_horas_operativas / NULLIF(prod.oee_horas_netas, 0)
             * prod.oee_pacas / NULLIF(prod.oee_pacas_ideales, 0)
             * (1 - prod.oee_horas_calidad / NULLIF(prod.oee_horas_operativas, 0)), 4) AS oee
FROM prod
JOIN dwh.dim_maquina m USING (maquina_key)
LEFT JOIN paro ON paro.anio_mes = prod.anio_mes AND paro.maquina_key = prod.maquina_key;

-- pareto de paros por codigo (sin los paros programados)
CREATE OR REPLACE VIEW dwh.v_pareto_codigos AS
WITH t AS (
    SELECT d.codigo, d.nombre_codigo, d.area_impacto, SUM(e.horas_paro) AS horas
    FROM dwh.fact_paro e
    JOIN dwh.dim_paro d USING (paro_key)
    WHERE d.clase_paro = 'no programado'
    GROUP BY d.codigo, d.nombre_codigo, d.area_impacto
)
SELECT codigo, nombre_codigo, area_impacto, ROUND(horas, 2) AS horas,
       ROUND(100 * horas / SUM(horas) OVER (), 2) AS pct,
       ROUND(100 * SUM(horas) OVER (ORDER BY horas DESC, codigo) / SUM(horas) OVER (), 2) AS pct_acumulado
FROM t
ORDER BY horas DESC;
