# 2. Diagnóstico de la fuente

## Qué es la fuente

El libro `SEGUIMIENTO TEMPERAS Y VINILOS Actividad.xlsm` tiene 21 hojas. Las que importan:

| Hoja | Contenido |
|---|---|
| `Registro` | Formulario "hora a hora" con tres botones de macro: ingreso total, ingreso de subcódigo y limpiar |
| `Base De Datos` | La tabla `T_baseDeDatos`: 8.208 filas y 58 columnas, del 1-ene-2022 al 28-mar-2025, cuatro máquinas |
| `Base de datos de Sub codigos` (oculta) | 1.252 filas con el detalle de los subcódigos 1, 3 y 5 |
| `TABLA CODIGOS`, `Tablas Desplegables` | Catálogos: códigos de paro, subcódigos, referencias con sus colores y unidades por paca, turnos, personal |
| `Tiempos`, `Calculadora de tiempos` | Cálculo de la meta por hora, la producción ideal y la eficiencia de cada registro |
| `TD_*`, `prod*`, `fallaMecanica`, `novPotencia`, `ajusteOperativo` | Tablas dinámicas y gráficos del informe mensual |

Cada fila de `Base De Datos` guarda: fecha, máquina, operaria, referencia, pacas producidas, horas trabajadas (en realidad, horas programadas del turno), turno, horas no trabajadas, tipo de paro, 18 pares de columnas con los minutos y las horas de cada código de paro, tres subcódigos y el tiempo total de paro.

## Cómo se calcula hoy

Las tablas dinámicas usan campos calculados sobre `T_baseDeDatos`:

- `% Productividad = (Horas trabajadas - Tiempo de paro) / Horas trabajadas`
- `% Paro = 1 - % Productividad`
- `% Código N = Código N en horas / Horas trabajadas` (N de 1 a 18)

Con eso se arman: producción general, producción por máquina (2024 frente a 2025), porcentaje de cada código por máquina y el detalle de los códigos 01, 03 y 05.

## Problemas de calidad de datos

Los conteos salen del ETL (`docs/reporte_etl.json`) y de los perfiles hechos sobre la hoja.

| # | Problema | Cuántos | Tratamiento |
|---|---|---|---|
| 1 | Filas duplicadas exactas (las 58 columnas iguales), típico de guardar dos veces | 42 filas (18,1 h de paro y 129 h programadas) | Se descartan (R2) |
| 2 | Filas de relleno: solo traen fecha y máquina, sin horas, pacas, paro ni horas sin trabajar | 222 filas | Se descartan (R3) |
| 3 | Columnas inservibles: `Unidades producidas cada minuto` y `Display por paca` vacías, `Unidad por display` trae el turno copiado | 3 columnas (687 valores erróneos) | No se cargan (R1) |
| 4 | Referencias con errores de escritura (`Alocdor`, `Stilo Kids`, `22 cc`, `(6col)`, `(12col)`) | 51 textos distintos que son 48 referencias; 490 valores corregidos | Se normalizan y se separan en marca, tamaño y colores (R4) |
| 5 | Dos esquemas de codificación en `Tipo de paro` ("17. PARO DE MAQUINA" y "[18] Paro de maquina por ventas") | 19 textos; 1.463 filas con el esquema viejo | Se mapean a un solo nombre con su código equivalente |
| 6 | Dos numeraciones de subcódigos ("4.2 SISTEMA DOSIFICADOR..." y "5.2 Sistema de dosificación...") y variantes de mayúsculas y espacios | 44 textos del subcódigo 1 que son 28 subcódigos; 945 filas con numeración vieja en el subcódigo 5 | Se convierten a una llave (`1.2.C`, `5.2`) y se toma la etiqueta del catálogo |
| 7 | Turno con 7 textos distintos y vacíos | 3.912 vacíos en la hoja | Se normalizan a 6 turnos más `Sin turno` |
| 8 | Operarias escritas de varias formas (`Marcela` y `Marcela C.`) y valores `No aplica` / `No` | 32 nombres, 545 "No aplica" | Se pasan a alias; `No aplica` queda como sin personal |
| 9 | Pacas atípicas: 11 registros de Vinilos_1 entre el 22 y el 29 de julio de 2023 con más de 1.000 pacas (el máximo normal es unas 380) | 11 filas | Se marcan `es_atipico` y no entran al rendimiento ni al OEE; los totales sí las conservan |
| 10 | Paro mayor que las horas programadas, horas programadas mayores a 12 y horas sin trabajar mayores a 24 | 3, 1 y 1 filas | Se conservan y se marcan |
| 11 | La hoja oculta de subcódigos repite lo que ya está en la base principal (códigos 3 y 5 coinciden al 100 %; el código 1 aparece duplicado) | 1.252 filas | No se carga, para no contar el paro dos veces |
| 12 | Referencia, turno y operaria no se registraban antes de octubre de 2023 | 0 % de las filas de producción de 2022, 22 % en 2023 y 93 % en 2024 | Las filas sin referencia usan la meta de la referencia más frecuente de su máquina y quedan marcadas `meta_estimada` |
| 13 | El código 18 es "Desinfección" en el formulario y "Paro de máquina por ventas" en el catálogo; el PDF del procedimiento lista 17 códigos | 8 filas usan la columna del código 18 | Se toma el nombre del formulario y se documenta |
| 14 | Huecos de registro largos por máquina | hasta 130 días sin registro en Vinilos_3 | No se imputan |

## Limitaciones del esquema actual de reporte

1. Solo calcula productividad y porcentaje por código. No calcula OEE (rendimiento y calidad), MTBF ni MTTR, ni la proporción preventivo/correctivo.
2. La meta por hora existe en el formulario pero no se guarda en la base, así que no se puede medir el rendimiento después.
3. La "productividad" del P-MTO-22 es en realidad disponibilidad: no mira cuánto se produjo frente a lo posible.
4. No hay comparaciones por turno, referencia u operaria; las tablas dinámicas son estáticas y se arman a mano cada mes.
5. La captura es manual y por papel: hay duplicados, columnas corridas, textos distintos para lo mismo y campos que antes no se llenaban.
6. No hay historia de cambios ni control de versiones, y un libro de Excel con macros no soporta varios usuarios a la vez.
7. Los nombres de operarias y personal de mantenimiento están en claro dentro del libro.
8. El informe llega una vez al mes: nadie se entera a tiempo cuando una máquina se detiene.
9. Hay un cambio de práctica de registro en octubre de 2023 (aparecen referencia, turno y operaria). La productividad promedio baja de 86,5 % a 67,8 % justo ahí, y parte de esa caída puede deberse a un registro más completo y no solo a peor desempeño.
