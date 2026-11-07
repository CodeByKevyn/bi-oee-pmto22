# 5. Diccionario de datos

Se generó a partir del catálogo de PostgreSQL (tipos y llaves) y de las reglas del ETL. En "Origen" se indica la hoja y la columna del Excel; "Generado" y "Derivado" son campos que no existen en el libro.

Las columnas con la regla "Tal como viene" de `stg` son una copia sin transformar. Las reglas de limpieza están en `docs/06_etl_y_calidad.md`.


## dwh.dim_fecha

Calendario continuo de 2022 a 2027. Dimensión generada, no viene del Excel.

| Columna | Tipo | Llave | Descripción | Regla de transformación | Origen |
|---|---|---|---|---|---|
| `fecha_key` | integer | PK | Fecha en formato aaaammdd | Se calcula de la fecha | Generado |
| `fecha` | date |  | Fecha del día | Rango continuo sin saltos | Generado |
| `anio` | smallint |  | Año | Año de la fecha | Generado |
| `semestre` | smallint |  | Semestre (1 o 2) | (mes - 1) / 6 + 1 | Generado |
| `trimestre` | smallint |  | Trimestre (1 a 4) | Trimestre de la fecha | Generado |
| `mes` | smallint |  | Número del mes | Mes de la fecha | Generado |
| `nombre_mes` | text |  | Nombre del mes en minúscula | Tabla de nombres en español | Generado |
| `anio_mes` | text |  | Año y mes, por ejemplo 2024-05 | aaaa-mm | Generado |
| `semana_iso` | smallint |  | Semana ISO 8601 | Semana ISO de la fecha | Generado |
| `dia_mes` | smallint |  | Día del mes | Día de la fecha | Generado |
| `dia_semana` | smallint |  | Día de la semana, lunes = 1 | Día de la semana + 1 | Generado |
| `nombre_dia` | text |  | Nombre del día | Tabla de nombres en español | Generado |
| `es_fin_de_semana` | boolean |  | Verdadero si es sábado o domingo | dia_semana >= 6 | Generado |

## dwh.dim_maquina

Las cuatro máquinas de envasado.

| Columna | Tipo | Llave | Descripción | Regla de transformación | Origen |
|---|---|---|---|---|---|
| `maquina_key` | integer | PK | Llave sustituta | Identidad de PostgreSQL | Generado |
| `maquina` | text |  | Nombre de la máquina (Vinilos_1 a Vinilos_4) | Tal como viene | `Base De Datos`.`Maquina` |
| `linea` | text |  | Línea de envasado; hoy cada máquina es una línea | Igual a maquina | `Base De Datos`.`Maquina` |
| `unidades_minuto` | numeric(6,1) |  | Velocidad nominal de la máquina en unidades por minuto | Valor más frecuente en la tabla de referencias de la máquina | `Tablas Desplegables`, tablas Tabla8, 14, 15 y 16, columna `unidades *minuto` |
| `factor_meta` | numeric(4,2) |  | Factor que ajusta la meta por hora de la máquina | Constante de la hoja de cálculo (0,93; 0,96; 1; 1) | `Calculadora de tiempos`, celda K10 |

## dwh.dim_turno

Turnos y jornadas normalizados.

| Columna | Tipo | Llave | Descripción | Regla de transformación | Origen |
|---|---|---|---|---|---|
| `turno_key` | integer | PK | Llave sustituta | Identidad de PostgreSQL | Generado |
| `turno` | text |  | Turno normalizado, por ejemplo Turno 1 (6am-2pm) | Los 7 textos del origen se llevan a 6 turnos más Sin turno | `Base De Datos`.`Turno` |
| `tipo_jornada` | text |  | Turno de 8 h, jornada especial o sin dato | Según el turno | Derivado |
| `hora_inicio` | time without time zone |  | Hora de inicio | Según el turno | Derivado |
| `hora_fin` | time without time zone |  | Hora de fin | Según el turno | Derivado |
| `horas_nominales` | numeric(4,1) |  | Duración nominal en horas | Según el turno | Derivado |
| `min_aseo` | smallint |  | Minutos de alimentación y aseo previstos | 40, o 70 en la jornada de 6am a 4:30pm | `Registro`, celda I18 |
| `min_pausa_activa` | smallint |  | Minutos de pausa activa previstos | 3, o 6 en la jornada de 6am a 4:30pm | `Registro`, celda I19 |

## dwh.dim_referencia

Referencias (productos). Dimensión de cambio lento tipo 2.

| Columna | Tipo | Llave | Descripción | Regla de transformación | Origen |
|---|---|---|---|---|---|
| `referencia_key` | integer | PK | Llave sustituta de la versión | Identidad de PostgreSQL; 0 = Sin referencia | Generado |
| `referencia` | text |  | Nombre de la referencia, sin errores de escritura | Se corrigen errores, espacios y formato (6 col) | `Base De Datos`.`Referencia` |
| `marca` | text |  | Marca, parte inicial del nombre | Texto antes del tamaño | Derivado del nombre |
| `tamano_cc` | integer |  | Tamaño del envase en cc | Número antes de cc | Derivado del nombre |
| `colores` | smallint |  | Cantidad de colores | Número dentro de (n col) | Derivado del nombre |
| `display_por_paca` | integer |  | Displays por paca | Se toma del maestro de referencias | `Tablas Desplegables`, columna `Display` |
| `unidades_por_paca` | integer |  | Unidades por paca | Se toma del maestro de referencias | `Tablas Desplegables`, columna `Unidades * paca` |
| `en_maestro` | boolean |  | Verdadero si la referencia existe en el maestro | Cruce con el maestro | Derivado |
| `vigente_desde` | date |  | Inicio de vigencia de la versión | 2022-01-01 en la primera carga | ETL |
| `vigente_hasta` | date |  | Fin de vigencia de la versión | 9999-12-31 mientras esté vigente | ETL |
| `es_vigente` | boolean |  | Verdadero si es la versión actual | Se actualiza al cerrar una versión | ETL |

## dwh.dim_personal

Personas (operarias, personal de mantenimiento) identificadas solo por un alias.

| Columna | Tipo | Llave | Descripción | Regla de transformación | Origen |
|---|---|---|---|---|---|
| `personal_key` | integer | PK | Llave sustituta | Identidad de PostgreSQL; 0 = Sin dato | Generado |
| `alias` | text |  | Seudónimo de la persona: P y 8 caracteres del SHA-256 del nombre con una sal | El nombre nunca llega a la base de datos | `Base De Datos`.`Operario` y `Personal involucrado` |
| `rol` | text |  | operaria, mantenimiento, otro o sin dato | Operaria si aparece en Operario; si no, según el área involucrada del subcódigo 5 | `Base De Datos`.`Área involucrada en subcodigo 5` |

## dwh.dim_paro

Códigos de paro con sus subcódigos. Dimensión construida con la clasificación propia.

| Columna | Tipo | Llave | Descripción | Regla de transformación | Origen |
|---|---|---|---|---|---|
| `paro_key` | integer | PK | Llave sustituta | Identidad de PostgreSQL | Generado |
| `codigo` | smallint |  | Código de paro, 1 a 18 | Número del código | `TABLA CODIGOS` |
| `nombre_codigo` | text |  | Código y nombre, por ejemplo [05] Ajuste operativo | Nombre del catálogo | `TABLA CODIGOS` y `Registro` |
| `area_impacto` | text |  | Área de impacto: Mantenimiento, Producción, Calidad, Almacén de materias primas, Paro programado, Ventas | Del catálogo; el 18 queda Sin definir | `Tablas Desplegables`, tabla Tabla2 |
| `subcodigo_nivel1` | text |  | Subcódigo de primer nivel (por ejemplo 1.2 Sistema de dosificación); Sin especificar si no aplica | Etiqueta del catálogo | `Tablas Desplegables`, columnas AQ a AU |
| `subcodigo_nivel2` | text |  | Subcódigo de segundo nivel (por ejemplo 1.2.C Cambio de válvula); Sin especificar si no aplica | Etiqueta del catálogo | `Tablas Desplegables`, columnas AQ a AU |
| `clase_paro` | text |  | programado (códigos 4, 15, 16, 17, 18) o no programado | Clasificación propia | Derivado |
| `tipo_perdida_oee` | text |  | disponibilidad, calidad (códigos 11 y 12) o programado | Clasificación propia | Derivado |

## dwh.fact_produccion_turno

Un registro de turno de una máquina, o un registro de tiempo sin programar.

| Columna | Tipo | Llave | Descripción | Regla de transformación | Origen |
|---|---|---|---|---|---|
| `produccion_key` | bigint | PK | Llave sustituta del hecho | Identidad de PostgreSQL | Generado |
| `fila_excel` | integer |  | Fila de la hoja de origen, para rastrear el dato | Número de fila | `Base De Datos`, fila |
| `fecha_key` | integer | FK a dim_fecha | Llave de dim_fecha | aaaammdd | `Base De Datos`.`Fecha` |
| `maquina_key` | integer | FK a dim_maquina | Llave de dim_maquina | Búsqueda por nombre | `Base De Datos`.`Maquina` |
| `turno_key` | integer | FK a dim_turno | Llave de dim_turno | Búsqueda del turno normalizado | `Base De Datos`.`Turno` |
| `referencia_key` | integer | FK a dim_referencia | Llave de dim_referencia | Versión vigente en la fecha; 0 si no hay referencia | `Base De Datos`.`Referencia` |
| `personal_key` | integer | FK a dim_personal | Llave de dim_personal (operaria) | 0 si es No aplica o vacío | `Base De Datos`.`Operario` |
| `tipo_registro` | text |  | turno con producción o tiempo sin programar | Con horas o pacas es turno; si solo hay horas sin trabajar es sin programar | Derivado |
| `horas_programadas` | numeric(6,2) |  | Horas del turno programadas | Nulo se convierte en 0 | `Base De Datos`.`Horas trabajadas` |
| `pacas_producidas` | numeric(10,1) |  | Pacas producidas | Nulo se convierte en 0 | `Base De Datos`.`Pacas producidas` |
| `horas_no_trabajadas` | numeric(6,2) |  | Horas sin trabajar (máquina sin programar) | Nulo se convierte en 0 | `Base De Datos`.`Horas no trabajadas` |
| `tipo_no_trabajo_codigo` | smallint |  | Código equivalente del tipo de paro, si lo tiene | Mapeo de los dos esquemas de codificación | `Base De Datos`.`Tipo de paro` |
| `tipo_no_trabajo` | text |  | Motivo por el que no se trabajó, con un nombre único | Mapeo de los dos esquemas de codificación | `Base De Datos`.`Tipo de paro` |
| `horas_paro_turno` | numeric(12,6) |  | Horas de paro de todo el turno (incluye las filas de subcódigo del mismo turno) | Suma de los eventos con la misma fecha, máquina, turno, operaria y referencia; si hay varias filas se reparte según las horas programadas | `Base De Datos`.`Codigo N en horas` (N de 1 a 18) |
| `horas_paro_programado` | numeric(12,6) |  | Horas de paro programado (códigos 4, 15, 16, 17, 18) | Igual que horas_paro_turno, solo esos códigos | `Base De Datos`.`Codigo N en horas` |
| `horas_paro_calidad` | numeric(12,6) |  | Horas de paro por reproceso y materia prima defectuosa (códigos 11 y 12) | Igual que horas_paro_turno, solo esos códigos | `Base De Datos`.`Codigo N en horas` |
| `horas_paro_disponibilidad` | numeric(12,6) |  | Horas de paro no programado sin calidad | paro total - programado - calidad, mínimo 0 | Derivado |
| `horas_programadas_netas` | numeric(12,6) |  | Horas programadas menos el paro programado | horas_programadas - horas_paro_programado, mínimo 0 | Derivado |
| `horas_operativas` | numeric(12,6) |  | Horas en que la máquina pudo producir | netas - paro de disponibilidad, mínimo 0 | Derivado |
| `meta_pacas_hora` | numeric(8,3) |  | Pacas por hora que debería producir con su referencia | 60 x factor de la máquina x unidades por minuto / unidades por paca | `Calculadora de tiempos`, fórmula de Producción ideal |
| `pacas_ideales` | numeric(12,3) |  | Pacas que se esperaban en las horas operativas | meta_pacas_hora x horas_operativas | Derivado |
| `es_atipico` | boolean |  | Verdadero si tiene más de 1.000 pacas | Umbral fijo, ver diagnóstico | Derivado |
| `sin_referencia` | boolean |  | Verdadero si el registro no trae referencia | referencia vacía | Derivado |
| `meta_estimada` | boolean |  | Verdadero si la meta salió de la referencia más frecuente de la máquina | Sin referencia o fuera del maestro | Derivado |
| `incluye_oee` | boolean |  | Verdadero si el registro entra al cálculo del OEE | Turno con producción, sin atípicos, con meta real y horas operativas > 0 | Derivado |

## dwh.fact_paro

Un evento de paro: un registro del Excel por cada código de paro con minutos.

| Columna | Tipo | Llave | Descripción | Regla de transformación | Origen |
|---|---|---|---|---|---|
| `paro_evento_key` | bigint | PK | Llave sustituta del evento | Identidad de PostgreSQL | Generado |
| `fila_excel` | integer |  | Fila de la hoja de origen | Número de fila | `Base De Datos`, fila |
| `fecha_key` | integer | FK a dim_fecha | Llave de dim_fecha | aaaammdd | `Base De Datos`.`Fecha` |
| `maquina_key` | integer | FK a dim_maquina | Llave de dim_maquina | Búsqueda por nombre | `Base De Datos`.`Maquina` |
| `turno_key` | integer | FK a dim_turno | Llave de dim_turno | Turno normalizado | `Base De Datos`.`Turno` |
| `referencia_key` | integer | FK a dim_referencia | Llave de dim_referencia | Versión vigente en la fecha | `Base De Datos`.`Referencia` |
| `personal_key` | integer | FK a dim_personal | Llave de dim_personal (operaria del registro) | 0 si no hay | `Base De Datos`.`Operario` |
| `paro_key` | integer | FK a dim_paro | Llave de dim_paro | Código y subcódigos del evento | `Base De Datos`.`Codigo de paro N` y los subcódigos 1, 3 y 5 |
| `personal_involucrado_key` | integer | FK a dim_personal | Llave de dim_personal (persona involucrada en el subcódigo 5) | Solo en el código 5; 0 en los demás | `Base De Datos`.`Personal involucrado` |
| `minutos_paro` | numeric(8,2) |  | Minutos del paro | Solo valores mayores que 0 | `Base De Datos`.`Codigo de paro N` |
| `horas_paro` | numeric(14,8) |  | Horas del paro | Columna generada: minutos / 60 | Derivado |

## rt.lectura_hora

Lecturas hora a hora (simuladas) que usa Grafana.

| Columna | Tipo | Llave | Descripción | Regla de transformación | Origen |
|---|---|---|---|---|---|
| `lectura_id` | bigint | PK | Llave sustituta | Identidad de PostgreSQL | Generado |
| `ts` | timestamp with time zone |  | Inicio de la hora | Hora simulada | Simulador |
| `maquina` | text |  | Nombre de la máquina | Igual que dim_maquina | Simulador |
| `turno` | text |  | Turno de la hora | Según la hora del día | Simulador |
| `referencia` | text |  | Referencia habitual de la máquina | Referencia más frecuente en el OEE | Simulador |
| `pacas` | numeric(8,2) |  | Pacas producidas en la hora | meta x (1 - minutos/60) x ruido | Simulador |
| `meta_pacas` | numeric(8,2) |  | Meta de pacas de la hora | Mediana de meta_pacas_hora de la máquina | dwh.fact_produccion_turno |
| `minutos_paro` | numeric(5,1) |  | Minutos de paro de la hora (0 a 60) | Distribución tomada de la historia | Simulador |
| `codigo_paro` | smallint |  | Código del paro principal | Muestreo con los pesos del paro no programado desde 2024 | Simulador |
| `escenario` | text |  | normal o falla | falla si se pidió con --falla | Simulador |

## stg.base_datos

Copia de la hoja Base De Datos con alias en vez de nombres. Solo la lee el ETL.

| Columna | Tipo | Llave | Descripción | Regla de transformación | Origen |
|---|---|---|---|---|---|
| `fila_excel` | integer | PK | Fila de la hoja de origen | Número de fila | `Base De Datos` |
| `fecha` | date |  | Fecha | Tal como viene | `Base De Datos`.`Fecha` |
| `mes` | text |  | Mes en texto | Tal como viene | `Base De Datos`.`Mes` |
| `anio` | text |  | Año en texto | Tal como viene | `Base De Datos`.`Año` |
| `maquina` | text |  | Máquina | Sin espacios sobrantes | `Base De Datos`.`Maquina` |
| `operaria_alias` | text |  | Alias de la operaria (no se guarda el nombre) | SHA-256 con sal | `Base De Datos`.`Operario` |
| `referencia_origen` | text |  | Referencia como se escribió | Solo se quitan espacios sobrantes | `Base De Datos`.`Referencia` |
| `pacas` | numeric(10,1) |  | Pacas producidas | Tal como viene | `Base De Datos`.`Pacas producidas` |
| `horas_trabajadas` | numeric(6,2) |  | Horas del turno | Tal como viene | `Base De Datos`.`Horas trabajadas` |
| `turno_origen` | text |  | Turno como se escribió | Tal como viene | `Base De Datos`.`Turno` |
| `horas_no_trabajadas` | numeric(6,2) |  | Horas sin trabajar | Tal como viene | `Base De Datos`.`Horas no trabajadas` |
| `tipo_paro_origen` | text |  | Tipo de paro como se escribió | Tal como viene | `Base De Datos`.`Tipo de paro` |
| `obs_paro` | text |  | Observación del paro (texto libre) | Tal como viene | `Base De Datos`.`Observaciones de paro` |
| `cod_01_min` | numeric(8,2) |  | Minutos del código de paro 1 | Tal como viene | `Base De Datos`.`Codigo de paro 1` |
| `cod_02_min` | numeric(8,2) |  | Minutos del código de paro 2 | Tal como viene | `Base De Datos`.`Codigo de paro 2` |
| `cod_03_min` | numeric(8,2) |  | Minutos del código de paro 3 | Tal como viene | `Base De Datos`.`Codigo de paro 3` |
| `cod_04_min` | numeric(8,2) |  | Minutos del código de paro 4 | Tal como viene | `Base De Datos`.`Codigo de paro 4` |
| `cod_05_min` | numeric(8,2) |  | Minutos del código de paro 5 | Tal como viene | `Base De Datos`.`Codigo de paro 5` |
| `cod_06_min` | numeric(8,2) |  | Minutos del código de paro 6 | Tal como viene | `Base De Datos`.`Codigo de paro 6` |
| `cod_07_min` | numeric(8,2) |  | Minutos del código de paro 7 | Tal como viene | `Base De Datos`.`Codigo de paro 7` |
| `cod_08_min` | numeric(8,2) |  | Minutos del código de paro 8 | Tal como viene | `Base De Datos`.`Codigo de paro 8` |
| `cod_09_min` | numeric(8,2) |  | Minutos del código de paro 9 | Tal como viene | `Base De Datos`.`Codigo de paro 9` |
| `cod_10_min` | numeric(8,2) |  | Minutos del código de paro 10 | Tal como viene | `Base De Datos`.`Codigo de paro 10` |
| `cod_11_min` | numeric(8,2) |  | Minutos del código de paro 11 | Tal como viene | `Base De Datos`.`Codigo de paro 11` |
| `cod_12_min` | numeric(8,2) |  | Minutos del código de paro 12 | Tal como viene | `Base De Datos`.`Codigo de paro 12` |
| `cod_13_min` | numeric(8,2) |  | Minutos del código de paro 13 | Tal como viene | `Base De Datos`.`Codigo de paro 13` |
| `cod_14_min` | numeric(8,2) |  | Minutos del código de paro 14 | Tal como viene | `Base De Datos`.`Codigo de paro 14` |
| `cod_15_min` | numeric(8,2) |  | Minutos del código de paro 15 | Tal como viene | `Base De Datos`.`Codigo de paro 15` |
| `cod_16_min` | numeric(8,2) |  | Minutos del código de paro 16 | Tal como viene | `Base De Datos`.`Codigo de paro 16` |
| `cod_17_min` | numeric(8,2) |  | Minutos del código de paro 17 | Tal como viene | `Base De Datos`.`Codigo de paro 17` |
| `cod_18_min` | numeric(8,2) |  | Minutos del código de paro 18 | Tal como viene | `Base De Datos`.`Codigo de paro 18` |
| `subcod_01_origen` | text |  | Subcódigo 1 como se escribió | Tal como viene | `Base De Datos`.`Sub Codigo de paro 1` |
| `subcod_03_origen` | text |  | Subcódigo 3 como se escribió | Tal como viene | `Base De Datos`.`Subcodigo 3` |
| `subcod_05_origen` | text |  | Subcódigo 5 como se escribió | Tal como viene | `Base De Datos`.`Subcodigo 5` |
| `area_subcod_05` | text |  | Área involucrada en el subcódigo 5 | Tal como viene | `Base De Datos`.`Área involucrada en subcodigo 5` |
| `personal_alias` | text |  | Alias de la persona involucrada | SHA-256 con sal | `Base De Datos`.`Personal involucrado` |
| `tiempo_paro_h` | numeric(8,4) |  | Tiempo de paro total en horas | Tal como viene | `Base De Datos`.`Tiempo de Paro` |
| `observaciones` | text |  | Observaciones (texto libre) | Tal como viene | `Base De Datos`.`Observaciones` |

## stg.carga_log

Registro de cada corrida del ETL con su reporte de calidad.

| Columna | Tipo | Llave | Descripción | Regla de transformación | Origen |
|---|---|---|---|---|---|
| `carga_id` | integer | PK | Número de corrida | Serial | Generado |
| `ejecutada_en` | timestamp with time zone |  | Fecha y hora de la corrida | now() | Generado |
| `archivo` | text |  | Nombre del libro cargado | Nombre del archivo | Parámetro del ETL |
| `reporte` | jsonb |  | Reporte de calidad en JSON | Resultado de la limpieza | ETL |
