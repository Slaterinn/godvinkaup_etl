#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR="${RUNTIME_DIR:-$HOME/docker/dbt-airflow}"
AIRFLOW_SERVICE="${AIRFLOW_SERVICE:-airflow-scheduler}"

cd "$RUNTIME_DIR"

echo "Validating Airflow DAGs using Docker Compose service: $AIRFLOW_SERVICE"

docker compose exec "$AIRFLOW_SERVICE" airflow dags list

echo "Airflow DAG validation completed."
