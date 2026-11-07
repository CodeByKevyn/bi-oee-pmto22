# 10. Base de datos y consultas analíticas

La base `bi_oee` se creó con los scripts de `sql/`, ejecutados desde DBeaver o por el ETL, en este orden:

| Script | Contenido |
|---|---|
| `01_esquemas.sql` | Esquemas `stg`, `dwh` y `rt`, y el rol `bi_lectura` |
| `02_staging.sql` | `stg.base_datos` (copia del libro) y `stg.carga_log` |
| `03_dimensiones.sql` | Las seis dimensiones y sus miembros "desconocido" |
| `04_hechos.sql` | `fact_produccion_turno` y `fact_paro` |
| `05_tiempo_real.sql` | `rt.lectura_hora` |
| `06_indices.sql` | Índices |
| `07_vistas.sql` | `dwh.v_kpi_maquina_mes` y `dwh.v_pareto_codigos` |
| `10_tiempo_real_vistas.sql` | Vistas que consume Grafana |
| `11_permisos.sql` | Permisos del rol de lectura |

## Restricciones y por qué

| Restricción | Dónde | Razón |
|---|---|---|
| Llave primaria sustituta (`identity`) | Todas las dimensiones y hechos | El Excel no tiene un identificador de fila estable; las llaves sustitutas permiten cambiar atributos y llevar historia sin tocar los hechos |
| `fecha_key` entero con formato `aaaammdd`, `fecha` única | `dim_fecha` | Unir por entero es más rápido, y la llave se lee a simple vista |
| `UNIQUE` en la llave natural (`maquina`, `turno`, `alias`, `codigo + subcódigos`, `referencia + vigente_desde`) | Dimensiones | Es lo que permite al ETL actualizar sin duplicar (`ON CONFLICT`) |
| `FOREIGN KEY` de cada hecho hacia todas sus dimensiones, `NOT NULL` | Hechos | Un hecho sin dimensión no se puede analizar; los datos que faltan apuntan al miembro desconocido (llave 0) en vez de quedar nulos |
| `CHECK (horas_programadas >= 0)`, `pacas_producidas >= 0`, `horas_no_trabajadas >= 0` | `fact_produccion_turno` | Valores negativos serían errores de digitación |
| `CHECK (minutos_paro > 0)` | `fact_paro` | Solo se guarda un evento cuando hay minutos |
| `CHECK` de `clase_paro` y `tipo_perdida_oee` | `dim_paro` | Solo se permiten los valores que usan las medidas del OEE |
| `CHECK (minutos_paro BETWEEN 0 AND 60)` y `UNIQUE (maquina, ts)` | `rt.lectura_hora` | Una lectura es de una hora; el simulador puede reintentar sin duplicar |
| `horas_paro` como columna generada (`minutos_paro / 60`) | `fact_paro` | Evita que las horas y los minutos queden en desacuerdo |
| Numéricos con 6 decimales en las horas | Hechos | Con 4 decimales la conciliación se desviaba 0,05 h; con 6 cuadra |
| `REVOKE` sobre `stg` | `bi_lectura` | `stg` guarda los textos libres del libro |

## Índices y por qué

| Índice | Consulta que lo usa |
|---|---|
| `fact_produccion_turno (fecha_key, maquina_key)` y `fact_paro (fecha_key, maquina_key)` | Casi todos los filtros: periodo y máquina |
| `fact_paro (paro_key)` | Pareto y jerarquía de paros |
| `turno_key` y `referencia_key` en producción; `turno_key` en paro | Análisis por turno y por referencia |
| `fila_excel` en ambos hechos | Rastrear un valor hasta la fila del libro y conciliar |
| `rt.lectura_hora (maquina, ts DESC)` y `(ts DESC)` | Grafana siempre pide la última ventana de una máquina |
| `dim_referencia (referencia, vigente_desde, vigente_hasta)` | Buscar la versión vigente de una referencia en una fecha |

Las primarias y las `UNIQUE` ya crean su índice. Los hechos tienen unas 6.600 y 16.500 filas, así que los índices ayudan poco al rendimiento actual; se dejaron pensando en que el modelo crezca con la lectura de los PLC.

## Consultas analíticas (`sql/08_consultas_analiticas.sql`)

| N.º | Pregunta | Técnica | Resultado destacado |
|---|---|---|---|
| 1 | ¿Qué máquina fue la mejor y la peor en OEE cada mes? | `RANK() OVER (PARTITION BY anio_mes)` | En marzo de 2025 la mejor fue Vinilos_3 (70,8 %) y la peor Vinilos_2 (50,6 %) |
| 2 | ¿Cómo va la productividad contra el mismo mes del año anterior? | `LAG` por máquina y mes | Compara el mismo mes aunque falten meses intermedios |
| 3 | ¿Cuántos códigos explican el 80 % del tiempo perdido? | Porcentaje acumulado con `SUM OVER` | 5 códigos suman 84,15 %: 05, 06, 07, 10 y 01 |
| 4 | ¿Cuáles son los 3 sistemas que más fallan en cada máquina? | `ROW_NUMBER` sobre la jerarquía de paros | Dosificación (1.2) en Vinilos_2, 3 y 4; alimentación de tapa (1.5) en Vinilos_1 |
| 5 | ¿Cuál es la tendencia de horas de paro? | Promedio móvil de 3 meses | Suaviza meses con muy pocas horas programadas |
| 6 | ¿Cuántas pacas van en el año? | Suma acumulada por año | Base del acumulado del año (YTD) en Power BI |
| 7 | ¿Qué turnos pierden más que el promedio de su máquina? | `AVG OVER` y diferencia | En Vinilos_2 el turno 3 pierde 46,0 % frente a un promedio de 40,8 % |
| 8 | ¿Qué días fueron anormalmente malos? | `PERCENT_RANK` (5 % peor) | El 26 de diciembre de 2023 Vinilos_1 perdió 18,8 h |
| 9 | ¿Cada cuánto falla una máquina y cuánto tarda en volver? | Agregaciones con subconsulta lateral | MTTR de Vinilos_1: 48,0 min en 2022 y 35,7 min en 2024; MTBF de 50,7 h a 92,4 h |

Un detalle de la consulta 9: antes dividía por las fallas la suma repetida de las horas programadas y daba un MTBF igual a las horas del año. Se corrigió para restar las horas de falla y dividir por el número de fallas, igual que la medida de Power BI.

Las fallas anteriores a octubre de 2023 se registraron con otro esquema, así que la mejora del MTBF puede deberse en parte a registrar menos fallas.

## Conciliación desde SQL

`sql/09_conciliacion.sql` compara el modelo con el libro por año y por código de paro, cuenta los eventos y turnos que cayeron en miembros "desconocido" y contrasta con la tabla dinámica `TD_prodMaq` del Excel (Vinilos_2, enero a marzo de 2024: 0,6793, 0,5757 y 0,5930, los mismos valores).
