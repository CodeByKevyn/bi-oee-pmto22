# 1. Usuarios y preguntas de negocio

La empresa fabrica vinilos y témperas y tiene cuatro líneas de envasado (Vinilos_1 a Vinilos_4). Hoy la información se registra a mano por turno, se pasa a un libro de Excel y de ahí salen las tablas dinámicas del informe mensual (procedimiento P-MTO-22).

## Quién usa la solución

| Usuario | Qué decide | Herramienta | Frecuencia |
|---|---|---|---|
| Alta dirección y comité mensual | Dónde invertir y qué planes de mantenimiento aprobar | Power BI | Mensual |
| Coordinador de mantenimiento | Qué sistemas intervenir, cuánto pesa el preventivo frente al correctivo | Power BI | Semanal y mensual |
| Jefe de producción / supervisor | Qué máquina, turno o referencia pierde más tiempo | Power BI y Grafana | Diaria |
| Operarias y técnicos de línea | Si la máquina está produciendo y qué paro está ocurriendo | Grafana | Hora a hora |
| Calidad y laboratorio | Cuánto tiempo se pierde por materia prima defectuosa, reproceso y esperas de aval | Power BI | Mensual |

## Preguntas que responde cada uno

**Alta dirección**
1. ¿Cómo evolucionan la productividad y el OEE de cada máquina por año?
2. ¿Cuántas horas se pierden al año por paros y cuántas de ellas son evitables (no programadas)?
3. ¿Qué máquinas están por debajo de la meta y desde cuándo?
4. ¿Cuánto tiempo de máquina no se programa por falta de demanda o de materia prima?

**Coordinador de mantenimiento**
5. ¿Qué sistemas de la máquina fallan más (código 01 por sistema y componente)?
6. ¿Cuánto tarda en promedio una reparación (MTTR) y cada cuánto falla una máquina (MTBF)?
7. ¿Qué proporción del tiempo de mantenimiento es preventivo y cuánta es correctivo?
8. ¿Cuántas horas se pierden esperando soporte de mantenimiento (código 02)?

**Jefe de producción**
9. ¿Qué turno tiene más paro que el promedio de su máquina?
10. ¿Qué referencias tienen más ajustes y limpiezas (códigos 05, 06 y 07)?
11. ¿Cómo va el mes frente al mismo mes del año anterior?

**Operación en línea**
12. ¿Qué máquinas están produciendo ahora y cuáles están paradas?
13. ¿Cuánto llevan perdido en las últimas 3 horas y por qué código?
14. ¿La producción de la hora está cumpliendo la meta?

**Calidad**
15. ¿Cuántas horas se pierden por materia prima defectuosa (12), reproceso (11) y espera de aval del laboratorio (13)?

## Qué capa atiende cada pregunta

Las preguntas 1 a 11 y la 15 necesitan historia, comparaciones y jerarquías: se responden en Power BI sobre el esquema `dwh`. Las preguntas 12 a 14 necesitan ver lo último que pasó y avisar: se responden en Grafana sobre `rt.lectura_hora`.
