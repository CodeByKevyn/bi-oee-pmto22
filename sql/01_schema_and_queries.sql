-- ============================================================
-- PROYECTO BI: CONTROL DE OEE Y ANÁLISIS DE PAROS (P-MTO-22)
-- Script: Vistas Analíticas para Grafana y Power BI
-- Motor: PostgreSQL
-- ============================================================

-- 1. VISTA PARA RESUMEN DE OEE POR MÁQUINA
CREATE OR REPLACE VIEW vw_oee_resumen_maquina AS
SELECT 
    maquina,
    SUM(horas_trabajadas) AS total_horas_trabajadas,
    SUM(tiempo_de_paro) AS total_tiempo_paro,
    ROUND(
        CAST(
            (SUM(horas_trabajadas) - SUM(tiempo_de_paro)) / NULLIF(SUM(horas_trabajadas), 0) * 100 
        AS NUMERIC), 
        2
    ) AS disponibilidad_pct
FROM public.seguimiento_vinilos
GROUP BY maquina;

-- 2. VISTA PARA MONITOREO DE PARETO DE PAROS (P-MTO-22)
CREATE OR REPLACE VIEW vw_pareto_paros AS
SELECT 
    codigo_de_paro_1,
    sub_codigo_de_paro_1,
    SUM(tiempo_de_paro) AS horas_totales_paro,
    COUNT(*) AS cantidad_eventos
FROM public.seguimiento_vinilos
WHERE codigo_de_paro_1 <> 'Sin Paro' AND codigo_de_paro_1 IS NOT NULL
GROUP BY codigo_de_paro_1, sub_codigo_de_paro_1
ORDER BY horas_totales_paro DESC;