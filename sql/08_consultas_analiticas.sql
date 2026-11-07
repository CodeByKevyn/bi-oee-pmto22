-- Consultas analiticas sobre el modelo dimensional. Cada una responde una pregunta de negocio.

-- 1. Que maquina fue la mejor y la peor en OEE cada mes?  (RANK)
SELECT anio_mes, maquina, oee,
       RANK() OVER (PARTITION BY anio_mes ORDER BY oee DESC) AS puesto
FROM dwh.v_kpi_maquina_mes
WHERE oee IS NOT NULL
ORDER BY anio_mes DESC, puesto;

-- 2. Como va la productividad de cada maquina frente al mismo mes del anio anterior?  (LAG por maquina y mes, comparativo entre periodos)
SELECT maquina, anio, mes, productividad_pmto22,
       CASE WHEN LAG(anio) OVER w = anio - 1 THEN LAG(productividad_pmto22) OVER w END AS productividad_anio_anterior,
       CASE WHEN LAG(anio) OVER w = anio - 1 THEN ROUND(productividad_pmto22 - LAG(productividad_pmto22) OVER w, 4) END AS variacion
FROM dwh.v_kpi_maquina_mes
WINDOW w AS (PARTITION BY maquina, mes ORDER BY anio)
ORDER BY maquina, anio, mes;

-- 3. Cuantos codigos de paro explican el 80 % del tiempo perdido?  (pareto con porcentaje acumulado)
SELECT codigo, nombre_codigo, horas, pct, pct_acumulado
FROM dwh.v_pareto_codigos
WHERE pct_acumulado - pct < 80;

-- 4. Cuales son los 3 sistemas que mas fallan en cada maquina?  (ROW_NUMBER sobre la jerarquia de paros)
WITH t AS (
    SELECT m.maquina, d.subcodigo_nivel1 AS sistema, SUM(e.horas_paro) AS horas
    FROM dwh.fact_paro e
    JOIN dwh.dim_paro d USING (paro_key)
    JOIN dwh.dim_maquina m USING (maquina_key)
    WHERE d.codigo = 1 AND d.subcodigo_nivel1 <> 'Sin especificar'
    GROUP BY m.maquina, d.subcodigo_nivel1
)
SELECT maquina, sistema, ROUND(horas, 1) AS horas
FROM (SELECT t.*, ROW_NUMBER() OVER (PARTITION BY maquina ORDER BY horas DESC) AS n FROM t) x
WHERE n <= 3
ORDER BY maquina, horas DESC;

-- 5. Tendencia de las horas de paro de cada maquina suavizada con 3 meses  (promedio movil)
SELECT maquina, anio_mes, ROUND(horas_paro, 1) AS horas_paro,
       ROUND(AVG(horas_paro) OVER (PARTITION BY maquina ORDER BY anio_mes ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 1) AS promedio_3_meses
FROM dwh.v_kpi_maquina_mes
ORDER BY maquina, anio_mes;

-- 6. Cuantas pacas llevamos acumuladas en el anio por maquina?  (suma acumulada, base de un YTD)
SELECT anio, mes, maquina, pacas,
       SUM(pacas) OVER (PARTITION BY anio, maquina ORDER BY mes) AS pacas_acumuladas_anio
FROM dwh.v_kpi_maquina_mes
ORDER BY anio, maquina, mes;

-- 7. Que turnos pierden mas tiempo que el promedio de su maquina?  (AVG OVER, diferencia contra el promedio)
WITH t AS (
    SELECT m.maquina, tu.turno,
           SUM(e.horas_paro) AS horas_paro,
           (SELECT SUM(p.horas_programadas) FROM dwh.fact_produccion_turno p WHERE p.maquina_key = e.maquina_key AND p.turno_key = e.turno_key) AS horas_prog
    FROM dwh.fact_paro e
    JOIN dwh.dim_maquina m USING (maquina_key)
    JOIN dwh.dim_turno tu USING (turno_key)
    WHERE tu.turno <> 'Sin turno'
    GROUP BY m.maquina, tu.turno, e.maquina_key, e.turno_key
)
SELECT maquina, turno, ROUND(100 * horas_paro / NULLIF(horas_prog, 0), 1) AS pct_paro,
       ROUND(AVG(100 * horas_paro / NULLIF(horas_prog, 0)) OVER (PARTITION BY maquina), 1) AS pct_paro_promedio_maquina,
       RANK() OVER (PARTITION BY maquina ORDER BY horas_paro / NULLIF(horas_prog, 0) DESC) AS puesto
FROM t
ORDER BY maquina, puesto;

-- 8. Que dias fueron anormalmente malos? (dias de cada maquina en el 5 % peor de paro)  (PERCENT_RANK)
WITH d AS (
    SELECT f.fecha, m.maquina, SUM(e.horas_paro) AS horas_paro
    FROM dwh.fact_paro e
    JOIN dwh.dim_fecha f USING (fecha_key)
    JOIN dwh.dim_maquina m USING (maquina_key)
    GROUP BY f.fecha, m.maquina
)
SELECT fecha, maquina, ROUND(horas_paro, 1) AS horas_paro
FROM (SELECT d.*, PERCENT_RANK() OVER (PARTITION BY maquina ORDER BY horas_paro) AS pr FROM d) x
WHERE pr >= 0.95
ORDER BY horas_paro DESC
LIMIT 20;

-- 9. Cada cuanto falla una maquina y cuanto tarda en volver?  (MTBF y MTTR del codigo 01)
SELECT m.maquina, f.anio,
       COUNT(*) AS fallas,
       ROUND(AVG(e.minutos_paro), 1) AS mttr_min,
       ROUND((p.horas - SUM(e.minutos_paro) / 60.0) / NULLIF(COUNT(*), 0), 1) AS mtbf_horas
FROM dwh.fact_paro e
JOIN dwh.dim_paro d USING (paro_key)
JOIN dwh.dim_maquina m USING (maquina_key)
JOIN dwh.dim_fecha f USING (fecha_key)
JOIN LATERAL (SELECT COALESCE(SUM(p2.horas_programadas), 0) AS horas
              FROM dwh.fact_produccion_turno p2
              JOIN dwh.dim_fecha f2 USING (fecha_key)
              WHERE p2.maquina_key = e.maquina_key AND f2.anio = f.anio) p ON true
WHERE d.codigo = 1
GROUP BY m.maquina, f.anio, p.horas
ORDER BY m.maquina, f.anio;
