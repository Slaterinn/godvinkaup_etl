cat > scripts/validate_airflow.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR="${RUNTIME_DIR:-$HOME/docker/dbt-airflow}"

if [ ! -d "$RUNTIME_DIR" ]; then
  echo "Runtime directory not found: $RUNTIME_DIR"
  exit 1
fi

cd "$RUNTIME_DIR"

docker compose exec airflow-scheduler airflow dags list
EOF
