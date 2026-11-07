# 3. Catálogo de indicadores

Los umbrales salen de la historia de los datos (percentiles de los valores mensuales por máquina, ver `sql/08_consultas_analiticas.sql`). Las fuentes son las tablas del esquema `dwh` y, para el tiempo real, `rt.lectura_hora`.

## A. Indicadores que hoy reporta el P-MTO-22

| ID | Indicador | Fórmula | Unidad | Granularidad | Meta o umbral | Fuente | Usuario |
|---|---|---|---|---|---|---|---|
| P1 | Productividad (P-MTO-22) | (horas programadas - horas de paro) / horas programadas | % | Máquina, mes, año | Meta 80 % (mediana mensual 79 %); alerta bajo 70 % (percentil 25: 68,7 %) | fact_produccion_turno, fact_paro | Dirección, producción |
| P2 | % de paro | 1 - P1 | % | Máquina, mes, año | Contrario de P1 | igual | Dirección |
| P3 | Producción en pacas | Suma de pacas producidas | pacas | Máquina, mes, año; comparativo contra el año anterior | Sin meta propia; se compara contra el mismo periodo del año anterior | fact_produccion_turno | Dirección |
| P4 | % de cada código de paro por máquina | horas del código / horas programadas | % | Máquina, mes, código | El código 05 y el 06 explican el 61 % del paro no programado | fact_paro | Producción, mantenimiento |
| P5 | Detalle del código 01 (falla electromecánica) | horas por sistema y componente | h | Máquina, sistema, componente | La dosificación (1.2) es el sistema que más falla en Vinilos_2, 3 y 4; en Vinilos_1 es la alimentación de tapa (1.5) | fact_paro, dim_paro | Mantenimiento |
| P6 | Detalle del código 03 (potencia: aire, energía, vapor) | horas por origen (3.1 a 3.5) | h | Máquina, origen | Sin meta; sirve para pedir acciones a servicios | fact_paro, dim_paro | Mantenimiento |
| P7 | Detalle del código 05 (ajuste operativo) | horas por sistema (5.1 a 5.11) y por área involucrada | h | Máquina, sistema, área | Sin meta; el área indica si lo resuelve la operaria o mantenimiento | fact_paro, dim_paro | Producción |

## B. Indicadores que el Excel no calcula y se proponen

| ID | Indicador | Fórmula | Unidad | Granularidad | Meta o umbral | Justificación |
|---|---|---|---|---|---|---|
| N1 | Disponibilidad (OEE) | horas operativas / horas programadas netas. Netas = programadas - paros programados (04, 15, 16, 17, 18) | % | Turno, máquina, mes | Meta 80 % (mediana 79,3 %) | Separa los paros que no se pueden evitar (aseo, pausa activa) de los que sí |
| N2 | Rendimiento (OEE) | pacas producidas / pacas ideales. Ideales = meta por hora x horas operativas | % | Turno, máquina, mes | Meta 90 % (mediana 93,7 %) | El Excel calcula la meta por hora pero no la guarda; aquí se recalcula con la fórmula de la hoja `Calculadora de tiempos`: 60 x factor de máquina x unidades por minuto / unidades por paca |
| N3 | Calidad (OEE, aproximada) | 1 - horas de reproceso y materia prima defectuosa (códigos 11 y 12) / horas operativas | % | Turno, máquina, mes | Meta 98 % (percentil 25: 98,3 %) | La fuente no registra unidades defectuosas, así que se mide con el tiempo perdido por calidad. Es una limitación declarada |
| N4 | OEE | N1 x N2 x N3, solo con filas de referencia conocida y sin valores atípicos | % | Turno, máquina, mes | Meta 70 % (mediana 68 %; percentil 75: 80 %) | Resume en un número lo que se pierde por paros, velocidad y calidad |
| N5 | Pareto de paros | horas por código y % acumulado, sin paros programados | h, % | Código, subcódigo | Cinco códigos suman el 84 % del paro no programado | Prioriza dónde actuar |
| N6 | MTTR | minutos promedio de un paro del código 01 | min | Máquina, mes | Referencia actual: 37,6 min (desde oct-2023) | Mide cuánto tarda en volver una máquina que falló |
| N7 | MTBF | (horas programadas - horas de paro por falla) / número de fallas | h | Máquina, mes | Sin meta; se sigue la tendencia | Mide cada cuánto falla |
| N8 | Preventivo frente a correctivo | horas del código 04 / horas del código 01 | h, % | Máquina, año | Hoy: 8,5 h preventivas contra 322,6 h correctivas (2,6 %) | Muestra que casi todo el mantenimiento es reactivo |
| N9 | Horas sin programar | suma de horas no trabajadas por tipo (falta de programación, ventas, materia prima) | h | Máquina, mes, tipo | Sin meta; es capacidad que no se usó | La dirección no ve este tiempo en el informe actual |
| N10 | Paro por turno | horas de paro / horas programadas de cada turno | % | Turno, máquina | Se compara cada turno contra el promedio de su máquina | Detecta turnos con problemas propios |
| N11 | Variación contra el año anterior | indicador del periodo - indicador del mismo periodo del año anterior (P1, N4, horas de paro) | pp, h | Mes, año | Positiva es mejora | Medida de inteligencia de tiempo en Power BI |
| N12 | Cumplimiento de la meta por hora | pacas de la hora / meta de pacas de la hora | % | Hora, máquina | Alerta bajo 70 % | Lo ve el operador en Grafana |
| N13 | Paro de las últimas 3 horas | minutos de paro de las últimas 3 horas / 180 | % | Máquina, tiempo real | Alerta sobre 50 % | Ver la justificación abajo |

## Umbral de la alerta (N13)

Para cada turno histórico se calculó qué parte del tiempo programado neto se perdió en paros no programados. Los percentiles son: mediana 16 %, percentil 75 30 %, percentil 90 46 % y percentil 95 58 %. Se fija la alerta en **50 %**: queda entre el percentil 90 y el 95, es decir, un nivel que solo supera cerca del 8 % de los turnos. En la simulación hora a hora, con operación normal, la ventana de 3 horas supera ese valor en el 1,5 % de las lecturas, así que casi no genera falsas alarmas, y una falla real la dispara a las dos horas de iniciada.
