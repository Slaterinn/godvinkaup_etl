#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR="${RUNTIME_DIR:-$HOME/docker/dbt-airflow}"
AIRFLOW_SERVICE="${AIRFLOW_SERVICE:-airflow-scheduler}"
DBT_PROJECT_DIR="${DBT_PROJECT_DIR:-/opt/airflow/godvinkaup_dbt}"

cd "$RUNTIME_DIR"

echo "Validating dbt using Docker Compose service: $AIRFLOW_SERVICE"
echo "dbt project dir: $DBT_PROJECT_DIR"

docker compose exec "$AIRFLOW_SERVICE" bash -lc "cd '$DBT_PROJECT_DIR' && dbt parse && dbt compile"

echo "dbt validation completed."
