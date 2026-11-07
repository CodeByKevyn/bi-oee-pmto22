# 9. Hallazgos y recomendaciones

Datos del 1 de enero de 2022 al 28 de marzo de 2025. Todas las cifras salen del modelo (`dwh`) y se pueden repetir con `sql/08_consultas_analiticas.sql`.

## Hallazgos

**1. La productividad baja cada año.** Medida como el P-MTO-22 (horas programadas menos horas de paro, sobre horas programadas):

| Año | Productividad | Horas programadas |
|---|---:|---:|
| 2022 | 87,7 % | 7.870 |
| 2023 | 79,2 % | 12.746 |
| 2024 | 72,6 % | 14.501 |
| 2025 (hasta marzo) | 70,2 % | 2.817 |

Desde 2024 las cuatro máquinas están por debajo de la meta de 80 %. Vinilos_2 es la más baja (62,5 % en 2024 y 57,2 % en 2025); en 2024 las mejores son Vinilos_3 y 4 (76,2 % y 76,9 %).

**2. Tres códigos concentran el paro.** Ajuste operativo (05), limpieza por derrame (06) y alistamiento o cambio de referencia (07) suman el 71,9 % de las horas de paro no programado; con otros dos códigos se llega al 84,2 %. Los tres son del proceso y de la operación, no de fallas de equipo.

**3. El mantenimiento es casi todo correctivo.** En el periodo hay 8,5 horas de mantenimiento preventivo y 322,6 horas de paro por falla (código 01). Cada falla tarda en promedio 37,6 minutos en resolverse (MTTR, 139 fallas desde octubre de 2023). La dosificación (1.2) es el sistema que más falla en Vinilos_2, 3 y 4, y la alimentación de tapa (1.5) en Vinilos_1.

**4. El ajuste operativo no tiene un responsable claro.** De las 1.814 horas del código 05, 707 no dicen qué área participó, 589 las atendió mantenimiento y 518 la operaria. Sin ese dato no se sabe si el problema se resuelve capacitando o reparando.

**5. Gran parte del tiempo ni siquiera se programa.** Hay más horas sin programar (41.344) que horas programadas (37.934). En 2023 casi todo es "paro de máquina por ventas" (14.317 h) y en 2022 pesa la falta de programación (5.036 h). Vinilos_2 tiene 13.890 horas sin programar frente a 4.204 programadas. Esto es capacidad sin usar, y el informe actual no la muestra.

**6. El turno cambia el resultado.** Desde octubre de 2023 el paro es 29,3 % en el turno 1, 27,1 % en el 2 y 25,3 % en el 3. Las jornadas especiales (6 am a 6 pm y 6 am a 4:30 pm) están alrededor del 40 %, aunque con pocas horas programadas, y las filas sin turno (37,2 %) esconden información.

**7. El OEE de las filas confiables está cerca de la meta, con diferencias grandes entre máquinas.** Vinilos_3 (79,6 %) y Vinilos_4 (77,8 %) superan la meta de 70 %; Vinilos_1 (61,0 %) y Vinilos_2 (60,2 %) no. Solo hay 2.427 turnos con referencia registrada y sin valores atípicos, por eso el OEE se lee como una indicación y no como una medida exacta.

## Recomendaciones

1. Atacar primero los códigos 05, 06 y 07. Para el 07, estandarizar el cambio de referencia (lista de pasos y herramientas listas) y programar las referencias por lotes para reducir cambios. Para el 06, revisar las causas de los derrames en Vinilos_3 y 4, donde pesan más.
2. Pasar del correctivo al preventivo: un plan por máquina centrado en dosificación y alimentación de tapa, y medir la relación preventivo contra correctivo (N8) cada mes.
3. Hacer obligatorio el campo "área involucrada" en el código 05 y cerrar la lista de opciones del formato, para que el dato sirva.
4. Llevar a la reunión de planeación las horas sin programar, con el motivo, para decidir si se comparte capacidad o se ajusta el plan de ventas.
5. Revisar por qué el turno 1 tiene más paro que el 3: hay que comprobar si se debe a los cambios de referencia, a la hora del día o a la práctica de cada equipo.
6. Usar en tiempo real el tablero de Grafana con la alerta de paro de 3 horas sobre el 50 %, y revisar el umbral cada trimestre con los datos nuevos.
7. A mediano plazo, tomar los datos directamente del PLC (ver `07_arquitectura_y_comparativo.md`).

## Precauciones al leer los números

- En octubre de 2023 cambió la forma de registrar: aparece el tipo de paro nuevo y los subcódigos. La productividad promedio mensual pasa de 86,5 % antes a 67,8 % desde esa fecha. Parte de esa caída puede ser un cambio de registro y no de desempeño, y no se puede separar con los datos que hay.
- 2025 solo tiene tres meses; comparar su total con años completos engaña, y por eso los comparativos usan el mismo periodo del año anterior.
- La calidad del OEE es una aproximación por tiempo de reproceso y materia prima defectuosa, porque el libro no trae unidades defectuosas.
- Para 4.047 filas de producción no hay referencia y la meta por hora es una estimación. Esas filas no entran al OEE.
- Las metas son propuestas tomadas de la historia, no valores oficiales de la planta. Hay que validarlas con producción.
