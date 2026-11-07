-- Conciliacion del modelo contra stg.base_datos (copia de la hoja del Excel).
-- La diferencia entre stg y dwh debe ser exactamente lo que descarto la limpieza (duplicados y filas vacias).

-- 1. filas y totales por anio
SELECT f.anio,
       COUNT(*) AS filas_stg,
       ROUND(SUM(COALESCE(s.horas_trabajadas, 0)), 2) AS horas_programadas_stg,
       ROUND(SUM(COALESCE(s.pacas, 0)), 1) AS pacas_stg,
       ROUND(SUM(COALESCE(s.tiempo_paro_h, 0)), 2) AS horas_paro_stg
FROM stg.base_datos s
JOIN dwh.dim_fecha f ON f.fecha = s.fecha
GROUP BY f.anio
ORDER BY f.anio;

SELECT f.anio,
       COUNT(*) AS filas_produccion_dwh,
       ROUND(SUM(p.horas_programadas), 2) AS horas_programadas_dwh,
       ROUND(SUM(p.pacas_producidas), 1) AS pacas_dwh,
       (SELECT ROUND(SUM(e.horas_paro), 2) FROM dwh.fact_paro e JOIN dwh.dim_fecha f2 USING (fecha_key) WHERE f2.anio = f.anio) AS horas_paro_dwh
FROM dwh.fact_produccion_turno p
JOIN dwh.dim_fecha f USING (fecha_key)
GROUP BY f.anio
ORDER BY f.anio;

-- 2. minutos de paro por codigo: stg contra fact_paro
WITH origen AS (
    SELECT c.codigo, SUM(c.minutos) AS minutos
    FROM stg.base_datos s
    CROSS JOIN LATERAL (VALUES
        (1, s.cod_01_min), (2, s.cod_02_min), (3, s.cod_03_min), (4, s.cod_04_min), (5, s.cod_05_min), (6, s.cod_06_min),
        (7, s.cod_07_min), (8, s.cod_08_min), (9, s.cod_09_min), (10, s.cod_10_min), (11, s.cod_11_min), (12, s.cod_12_min),
        (13, s.cod_13_min), (14, s.cod_14_min), (15, s.cod_15_min), (16, s.cod_16_min), (17, s.cod_17_min), (18, s.cod_18_min)
    ) AS c(codigo, minutos)
    GROUP BY c.codigo
), destino AS (
    SELECT d.codigo, SUM(e.minutos_paro) AS minutos
    FROM dwh.fact_paro e JOIN dwh.dim_paro d USING (paro_key)
    GROUP BY d.codigo
)
SELECT o.codigo, o.minutos AS minutos_stg, COALESCE(d.minutos, 0) AS minutos_dwh, o.minutos - COALESCE(d.minutos, 0) AS diferencia
FROM origen o LEFT JOIN destino d USING (codigo)
ORDER BY o.codigo;

-- 3. integridad: eventos y turnos que cayeron en miembros "desconocido"
SELECT 'produccion sin referencia' AS control, COUNT(*) AS filas FROM dwh.fact_produccion_turno WHERE referencia_key = 0
UNION ALL SELECT 'produccion sin personal', COUNT(*) FROM dwh.fact_produccion_turno WHERE personal_key = 0
UNION ALL SELECT 'produccion sin turno', COUNT(*) FROM dwh.fact_produccion_turno p JOIN dwh.dim_turno t USING (turno_key) WHERE t.turno = 'Sin turno'
UNION ALL SELECT 'paro sin personal involucrado', COUNT(*) FROM dwh.fact_paro WHERE personal_involucrado_key = 0;

-- 4. contra la tabla dinamica del Excel (hoja TD_prodMaq, productividad de Vinilos_2 en 2024)
SELECT mes, productividad_pmto22,
       CASE mes WHEN 1 THEN 0.6793456032719836 WHEN 2 THEN 0.5757188498402557 WHEN 3 THEN 0.5929936305732484 END AS valor_en_excel,
       ABS(productividad_pmto22 - CASE mes WHEN 1 THEN 0.6793456032719836 WHEN 2 THEN 0.5757188498402557 WHEN 3 THEN 0.5929936305732484 END) < 0.0001 AS coincide
FROM dwh.v_kpi_maquina_mes
WHERE maquina = 'Vinilos_2' AND anio = 2024 AND mes IN (1, 2, 3)
ORDER BY mes;
