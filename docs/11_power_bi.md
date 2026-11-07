# 11. Informe de Power BI

El proyecto está en `powerbi/BI_OEE.pbip`. Se abre con Power BI Desktop y se conecta a PostgreSQL (`dwh`) en modo importar.

## Formato PBIP y por qué

Se guardó como proyecto de Power BI (PBIP) y no como `.pbix`:

- El `.pbix` es un binario comprimido. En Git no se ve qué medida o relación cambió, y dos personas no pueden combinar su trabajo.
- El PBIP separa el modelo semántico (archivos TMDL, uno por tabla) y el informe (`report.json`). Cada cambio queda como una diferencia de texto en un commit.
- No guarda credenciales ni datos: el servidor y la base son parámetros (`Servidor` y `BaseDeDatos`) y los datos se cargan al actualizar.

Los archivos `.pbi/localSettings.json` y `cache.abf` quedan fuera del repositorio (`.gitignore`).

## Conexión

Cada tabla se importa con una consulta de Power Query del tipo `PostgreSQL.Database(Servidor, BaseDeDatos)` sobre el esquema `dwh`. Se eligió importar y no DirectQuery porque los datos históricos cambian una vez al día como máximo, y así las medidas de inteligencia de tiempo responden rápido. Lo que necesita estar al segundo está en Grafana.

## Modelo semántico

Es el mismo modelo en estrella del documento 4: dos hechos (`fact_produccion_turno`, `fact_paro`) y seis dimensiones, con 12 relaciones de uno a muchos.

- `fact_paro` tiene dos relaciones hacia `dim_personal`: la de la operaria (activa) y la del personal involucrado en el ajuste (inactiva). La segunda se usa con `USERELATIONSHIP` en la medida `Horas Paro (personal involucrado)`.
- `dim_fecha` está marcada como tabla de fechas, que es lo que habilita las funciones de tiempo.
- Jerarquías: fechas (año, trimestre, mes, día), **paros** (área de impacto, código, subcódigo 1, subcódigo 2), referencias, turnos y personal.
- Las llaves están ocultas; el usuario ve solo atributos y medidas.

## Medidas (tabla `Medidas`)

| Carpeta | Medidas |
|---|---|
| 01. Base | Horas Programadas, Horas Paro, Horas Paro No Programado, Horas Paro Programado, Pacas Producidas, Horas Sin Programar, Eventos de Paro |
| 02. P-MTO-22 | Productividad P-MTO-22, % Paro |
| 03. OEE (base confiable) | Horas Netas, Horas Operativas, Horas de Calidad, Pacas, Pacas Ideales, Disponibilidad, Rendimiento, Calidad, OEE, Meta OEE |
| 04. Paros y Pareto | Horas Paro Falla (código 01), Pareto Acumulado %, Horas Paro (personal involucrado) |
| 05. Confiabilidad | Fallas (código 01), MTTR (min), MTBF (h) |
| 06. Inteligencia de tiempo | Horas Paro Año Anterior, Productividad Año Anterior, OEE Año Anterior, Variación de horas y de productividad, Pacas y Horas de Paro Acumuladas del Año (YTD), Promedio Móvil 3 Meses |

Las medidas del OEE usan solo las filas marcadas `incluye_oee` (referencia conocida y sin valores atípicos). Ejemplos:

```
Productividad P-MTO-22 = DIVIDE([Horas Programadas] - [Horas Paro], [Horas Programadas])

OEE = [Disponibilidad] * [Rendimiento] * [Calidad]

Productividad Año Anterior =
    CALCULATE([Productividad P-MTO-22], SAMEPERIODLASTYEAR(dim_fecha[fecha]))

Pacas Acumuladas Año (YTD) = TOTALYTD([Pacas Producidas], dim_fecha[fecha])
```

El Pareto acumulado suma las horas de los códigos que tienen igual o más horas que el código actual y las divide entre el total visible (`ALLSELECTED`), por eso cambia con las segmentaciones y no necesita una columna de orden.

## Páginas

La navegación es con cuatro botones iguales en la parte superior de cada página.

| Página | Qué muestra | Pregunta que responde |
|---|---|---|
| Resumen | Tarjetas de OEE, disponibilidad, rendimiento, calidad y productividad; OEE por mes contra la meta; OEE por máquina; horas de paro y programadas por año; paro por marca. Segmentaciones de año, máquina y turno | ¿Cómo va la planta y cuál es la brecha contra la meta? |
| Paros | Pareto de códigos (columnas y línea de porcentaje acumulado); barras y matriz con la jerarquía de paros, que se despliega de área de impacto a código y a subcódigos; MTTR y eventos | ¿Qué paros pesan más y de qué sistema vienen? |
| Máquinas y turnos | Disponibilidad y OEE por turno; horas de paro y sin programar por máquina; matriz máquina por turno | ¿Qué máquina o turno pierde más tiempo? |
| Comparativo anual | Productividad por mes y año; horas de paro contra el año anterior; pacas acumuladas del año; promedio móvil de 3 meses; tarjetas de variación | ¿Mejoramos o empeoramos frente al año pasado? |

## Cómo se probó

El proyecto se abrió en Power BI Desktop sin errores del modelo ni del informe (el panel de problemas quedó en cero) y se actualizó contra una base PostgreSQL con los datos cargados por el ETL. Las medidas se contrastaron con el SQL: la productividad por año (87,7 %, 79,2 %, 72,6 % y 70,2 %), el MTTR y el MTBF por máquina dan los mismos valores que las consultas 3 y 9. Los datos se cargan al actualizar con las credenciales del equipo de cada persona.

Las capturas de las cuatro páginas están en el documento de entrega.
