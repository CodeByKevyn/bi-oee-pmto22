# 12. Tablero de Grafana y simulación hora a hora

Grafana atiende la pregunta "qué está pasando ahora" (documento 7). Todo se carga solo al iniciar, desde archivos del repositorio:

| Archivo | Qué define |
|---|---|
| `grafana/provisioning/datasources/postgres.yaml` | Conexión a PostgreSQL con el usuario de solo lectura. Servidor, base, usuario y contraseña salen de variables de entorno |
| `grafana/provisioning/dashboards/dashboards.yaml` | Carpeta `OEE` y ruta del tablero |
| `grafana/dashboards/oee_operativo.json` | Tablero "Monitoreo operativo de las líneas de envasado" |
| `grafana/provisioning/alerting/alertas.yaml` | Punto de contacto, política de notificación y cuatro reglas de alerta |

## Conexión

El data source `BI OEE PostgreSQL` apunta a la base `bi_oee` con el usuario `grafana_ro`, que pertenece al rol `bi_lectura` (ve `dwh` y `rt`, no ve `stg`). Docker lo crea con `docker/12_usuario_grafana.sh`.

## Datos en tiempo real

El ETL histórico llena `dwh`. Para el tiempo real, `etl/simulador_hora.py` escribe en `rt.lectura_hora` una lectura por máquina y por hora: turno, referencia, pacas, meta de pacas de esa hora, minutos de paro y código del paro. Los parámetros salen de la historia:

- La meta por hora es la mediana de cada máquina.
- La referencia es la más frecuente de la máquina.
- El código del paro se sortea con la frecuencia que tuvo desde 2024.
- Cada hora tiene 55 % de probabilidad de paro, con duración exponencial (máximo 40 minutos) calibrada con el promedio histórico de minutos no programados por hora.

Un reloj virtual hace que cada hora simulada dure unos pocos segundos (`--segundos-por-hora`). Primero escribe 24 horas de historia (`--prefill 24`) y luego sigue hora a hora. Con `--falla Vinilos_3` una máquina queda parada varias horas seguidas.

## Paneles

| Panel | Tipo | Consulta | Para qué |
|---|---|---|---|
| Estado actual por máquina | Stat | `rt.v_estado_actual`: última lectura de cada máquina | Ver si cada máquina está produciendo, con paros o parada |
| Cumplimiento de la meta por hora (%) | Serie de tiempo | pacas / meta de pacas de cada hora | Detectar caídas de ritmo |
| Minutos de paro por hora | Serie de tiempo | `minutos_paro` por máquina | Ver cuándo y cuánto se para |
| Paro en las últimas 3 horas (%) | Indicador (gauge) | `rt.v_ultimas_3h`, con umbrales en 30 % y 50 % | Es lo mismo que vigila la alerta |
| Paros por código en el rango de tiempo | Tabla | Horas con paro y minutos por código | Qué causa el paro ahora |
| Estado de las alertas | Lista de alertas | Reglas de la carpeta OEE | Ver cuál disparó |

Variables del tablero: `maquina` (varias opciones, se llena desde la base) y `turno`. El rango de tiempo va de las últimas 24 horas hasta 12 horas hacia delante y se refresca cada 5 segundos.

## Alerta

Cuatro reglas (una por máquina) que evalúan cada 10 segundos:

```sql
SELECT paro_pct::float AS paro_pct_3h
FROM rt.v_ultimas_3h
WHERE maquina = 'Vinilos_1'
```

Se dispara cuando `paro_pct_3h > 50`, sin tiempo de espera (`for: 0s`), porque la ventana de 3 horas ya es una forma de filtrar. Si no llegan datos queda en OK. El aviso va al punto de contacto `mantenimiento`, agrupado por alerta y máquina, y se repite cada 4 horas mientras siga activa.

**Por qué 50 %.** El nivel queda entre el percentil 90 (46 %) y el 95 (58 %) del paro no programado por turno en la historia; solo lo supera cerca del 8 % de los turnos. En la simulación con operación normal la ventana lo supera en el 1,5 % de las lecturas. Detalle en el documento 3.

La dirección del punto de contacto es un ejemplo (`mantenimiento@planta.example`). Para que llegue el aviso hay que configurar SMTP en Grafana o cambiar el receptor por Telegram, Slack o un webhook.

## Demostración hora a hora

Comando para la demostración:

```bash
python etl/simulador_hora.py --prefill 24 --segundos-por-hora 5 --limpiar --falla Vinilos_3 --falla-en 6 --falla-horas 5
```

Después de 24 horas de historia normal, a las 6 horas Vinilos_3 se detiene 5 horas seguidas. Resultado de una corrida de prueba (semilla 7), con el paro de la ventana de 3 horas de esa máquina:

| Hora | Minutos de paro | Código | Paro en 3 h | Alerta |
|---|---:|---:|---:|:-:|
| 00:00 | 40,0 | 6 | 29,4 % | no |
| 01:00 | 0,0 | | 29,4 % | no |
| 02:00 | 40,0 | 5 | 44,4 % | no |
| 03:00 | 8,3 | 6 | 26,8 % | no |
| 04:00 | 59,1 | 1 | 59,7 % | sí |
| 05:00 | 58,5 | 1 | 69,9 % | sí |
| 06:00 | 56,3 | 1 | 96,6 % | sí |
| 07:00 | 59,9 | 1 | 97,1 % | sí |
| 08:00 | 55,0 | 1 | 95,1 % | sí |
| 09:00 | 9,0 | 8 | 68,8 % | sí |

En esta corrida la alerta salta en la primera hora de la falla porque la ventana ya traía 40 minutos de la hora anterior. Con una ventana limpia salta en la segunda hora. Cuando la máquina se recupera la alerta sigue unas horas más, hasta que las horas de paro salen de la ventana.

## Qué se probó

- Las consultas de todos los paneles, de las variables y de las reglas se ejecutaron contra la base de datos con los filtros ya expandidos.
- El simulador se corrió contra PostgreSQL, incluido el escenario de falla.
- Las vistas de tiempo real devuelven un estado por máquina y la ventana de 3 horas.

Falta confirmar, en una instancia de Grafana con el plugin de PostgreSQL, que el tablero y las reglas se cargan por provisioning y que la alerta pasa a estado "Firing" con la simulación.
