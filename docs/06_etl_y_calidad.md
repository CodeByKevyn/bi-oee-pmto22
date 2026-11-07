# 6. ETL y calidad de datos

## Herramienta y por qué

El ETL es un programa de Python (`etl/run_etl.py`) con tres librerías: `openpyxl` para leer el libro, `pandas` para limpiar y `pg8000` para cargar en PostgreSQL.

- El libro tiene 21 hojas, macros y tablas en rangos fijos; leerlo y aplicar 14 reglas de limpieza se hace mejor con código que con una herramienta gráfica.
- Todo queda en texto y se versiona en Git. Power Query guardaría las reglas dentro de un archivo binario o de un informe.
- Se ejecuta con un solo comando y se puede repetir desde cero.
- `pg8000` está escrito solo en Python. Se eligió sobre `psycopg2` porque en el equipo de desarrollo Windows bloqueó la DLL de `psycopg` (Control de aplicaciones), y así el ETL corre igual en cualquier equipo.
- Se descartó Airflow porque hay una sola carga por lotes y no hay dependencias entre tareas; para programarla basta cron o el Programador de tareas.

## Pasos

1. **Extracción** (`etl/extraccion.py`): lee `Base De Datos` y los catálogos de `Tablas Desplegables` por el rango de cada tabla del libro.
2. **Limpieza** (`etl/transformacion.py`, función `limpiar`): aplica las reglas de la tabla de abajo.
3. **Modelo** (`construir_modelo`): arma las dimensiones, desagrega los 18 códigos de paro en eventos y calcula las horas operativas y la meta por hora.
4. **Carga** (`etl/carga.py`): crea el esquema si no existe, copia el libro a `stg` (con alias en lugar de nombres), actualiza las dimensiones sin cambiar sus llaves y recarga los hechos en una sola transacción.
5. **Conciliación**: compara los totales del libro contra el modelo.

Comandos:

```
python etl/run_etl.py              # carga completa, se puede repetir
python etl/run_etl.py --reset      # borra los esquemas y empieza de cero
python etl/run_etl.py --solo-limpieza
```

## Reglas de limpieza y su efecto

| Regla | Qué hace | Filas antes | Filas después | Efecto |
|---|---|---:|---:|---|
| R1 | Descarta 3 columnas inservibles | 58 columnas | 55 columnas | Quita 2 columnas vacías y una con el turno copiado |
| R2 | Elimina filas duplicadas exactas | 8.208 | 8.166 | -42 filas, -18,1 h de paro, -129 h programadas, -1.019 pacas |
| R3 | Elimina filas de relleno (sin horas, pacas, paro ni horas sin trabajar) | 8.166 | 7.944 | -222 filas, sin efecto en los totales |
| R4 | Normaliza texto: referencias (490 valores corregidos), turnos, tipo de paro (1.460 filas con el esquema viejo), subcódigos y alias de 32 nombres | 7.944 | 7.944 | 51 referencias pasan a 48; 7 turnos a 6 más `Sin turno` |
| R5 | Marca pacas atípicas (11) y paros mayores que las horas (3) | 7.944 | 7.944 | Las atípicas no entran al OEE; siguen en los totales |
| R6 | Separa personas por rol y las seudonimiza | 7.944 | 7.944 | Los nombres no llegan a la base |

Resultado de la limpieza (7.944 filas): 5.138 turnos con producción, 1.460 registros de tiempo sin programar y 1.346 filas que solo traen paro (subcódigos), que se cargan como eventos.

El modelo queda con 6.598 filas en `fact_produccion_turno` y 16.482 eventos en `fact_paro`.

## Conciliación

El libro y el modelo deben coincidir una vez se suma lo que descartó la limpieza.

| Total | Excel | Modelo | Diferencia | Descartado en la limpieza | Cuadra |
|---|---:|---:|---:|---:|:-:|
| Horas programadas | 38.063,35 | 37.934,35 | 129,00 | 129,00 | sí |
| Pacas | 378.778 | 377.759 | 1.019 | 1.019 | sí |
| Horas sin trabajar | 41.519,85 | 41.343,85 | 176,00 | 176,00 | sí |
| Horas de paro | 8.449,65 | 8.431,54 | 18,12 | 18,12 | sí |

La conciliación se calcula en cada corrida (`docs/reporte_etl.json`) y el ETL termina con error si algún total no cuadra. Además, `sql/09_conciliacion.sql` repite la comparación por año y por código de paro desde la base de datos.

La prueba externa más fuerte: la productividad de Vinilos_2 en enero, febrero y marzo de 2024 que calcula `dwh.v_kpi_maquina_mes` es 0,6793, 0,5757 y 0,5930, los mismos valores de la tabla dinámica `TD_prodMaq` del propio Excel.

## Idempotencia

Se puede ejecutar varias veces sin duplicar nada:

- Las dimensiones se actualizan con `INSERT ... ON CONFLICT` sobre su llave natural; las llaves sustitutas no cambian.
- Los hechos se vacían y se vuelven a cargar dentro de la misma transacción: si algo falla, queda la carga anterior.
- Se comprobó con tres corridas seguidas: mismos conteos y la misma huella MD5 de los dos hechos.

## Decisiones que conviene conocer

- Los paros de un turno vienen en filas distintas (la fila del turno y varias filas de subcódigo). Para calcular las horas operativas de cada turno se suman los eventos que tienen la misma fecha, máquina, turno, operaria y referencia, y si hay varias filas de producción con esa llave se reparte el paro según las horas programadas. 57,9 horas de paro no encuentran fila de producción y solo quedan en `fact_paro`.
- La hoja oculta de subcódigos no se carga, porque repite lo que ya trae la base principal.
- El maestro de referencias tiene 2 filas repetidas y una referencia con unidades por paca distintas entre máquinas; se toma la primera. Hay 5 referencias usadas que no están en el maestro.
- Las filas sin referencia (4.047 de producción) usan la referencia más frecuente de su máquina para estimar la meta y quedan marcadas `meta_estimada`. El OEE solo usa las 2.427 filas con referencia real y sin atípicos.

## Programación

Para correrlo cada madrugada con cron:

```
0 5 * * * cd /ruta/bi-oee-pmto22 && python etl/run_etl.py
```

En Windows se crea una tarea diaria en el Programador de tareas con el mismo comando.
