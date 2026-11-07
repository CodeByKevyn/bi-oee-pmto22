#!/bin/sh
# crea el usuario de solo lectura que usa Grafana (se ejecuta una vez, al crear el volumen)
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
CREATE ROLE "$GRAFANA_DB_USER" LOGIN PASSWORD '$GRAFANA_DB_PASSWORD' IN ROLE bi_lectura;
EOSQL
