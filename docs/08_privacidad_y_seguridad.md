# 8. Datos personales y seguridad de acceso

## Qué datos personales hay

El libro de Excel identifica por nombre a las operarias de las máquinas (32 nombres) y al personal involucrado en los ajustes (operarias, personal de mantenimiento y de otras áreas, algunos con nombre y apellidos completos). Los campos de observaciones son texto libre y podrían traer nombres. Medir producción o paros por persona es información laboral de personas identificadas: según la Ley 1581 de 2012 (protección de datos personales en Colombia) es dato personal y exige finalidad clara, uso solo para esa finalidad, acceso restringido y medidas de seguridad (artículo 4, principios).

Los datos de las máquinas (horas, pacas, minutos de paro) no son datos personales.

## Qué se hizo

| Medida | Dónde |
|---|---|
| Se seudonimiza al leer: el nombre se reemplaza por un alias (`P` más 8 caracteres del SHA-256 del nombre con una sal). Los nombres nunca llegan a PostgreSQL | `etl/transformacion.py` (`seudonimo`) |
| La sal sale de una variable de entorno (`PSEUDO_SALT`), no del repositorio | `.env.example` |
| Los textos libres (observaciones) solo existen en `stg`, que no ve el rol de BI; no pasan al modelo | `sql/11_permisos.sql` |
| El modelo conserva solo el alias y el rol (operaria o mantenimiento) | `dwh.dim_personal` |
| El libro y cualquier CSV con nombres no se versionan | `.gitignore` (`data/raw/`) |
| Las herramientas de BI se conectan con un rol de solo lectura que ve `dwh` y `rt`, y no ve `stg` | `bi_lectura` en `sql/01_esquemas.sql` y `sql/11_permisos.sql` |
| Grafana guarda la contraseña del data source cifrada y la toma de una variable de entorno; acceso anónimo y registro de usuarios desactivados | `grafana/provisioning`, `docker-compose.yml` |
| El proyecto de Power BI solo guarda el servidor y la base como parámetros, sin credenciales | `powerbi/BI_OEE.SemanticModel/definition/expressions.tmdl` |
| Ninguna contraseña ni cadena de conexión está en el código: todo sale de `.env` | `.env.example` |

El alias es una seudonimización, no una anonimización: quien tenga la sal y la lista de nombres puede volver a identificar a las personas. Por eso se sigue tratando como dato personal.

## Qué se recomienda y no está implementado

1. Aviso de privacidad y autorización de las personas cuyos datos se tratan, y un responsable del tratamiento.
2. Definir por escrito que las métricas por operaria sirven para mejorar el proceso y no para sanciones sin revisión humana.
3. En Power BI, no publicar segmentaciones por alias en informes de amplia circulación y agregar seguridad a nivel de fila: un rol por máquina o línea (`dim_maquina[maquina] = "Vinilos_1"`) para que cada supervisor vea la suya.
4. En Grafana, una organización o carpeta por área: operación con rol de lector, mantenimiento con rol de editor y solo el administrador con acceso a los data sources.
5. Una regla de conservación: cuánto tiempo se guarda el detalle por persona.
6. Cambiar las contraseñas de PostgreSQL y de Grafana periódicamente, y usar usuarios distintos para el ETL (escritura) y para las herramientas de BI (lectura).

## Incidente en el historial del repositorio

El primer commit del repositorio subió un script con una contraseña de desarrollo de PostgreSQL y un CSV con los nombres de las operarias. Ambos se retiraron del código actual (ahora la contraseña sale de `.env` y los datos están en `.gitignore`), pero siguen en el historial de Git. Esa contraseña debe considerarse comprometida: hay que cambiarla en PostgreSQL. Si el repositorio es público, conviene volverlo privado o limpiar el historial.
