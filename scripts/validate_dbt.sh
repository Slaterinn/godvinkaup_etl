cat > scripts/validate_dbt.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if command -v dbt >/dev/null 2>&1; then
  cd godvinkaup_dbt
  dbt parse
  dbt compile
else
  echo "dbt is not installed on the host."
  echo "Run dbt validation inside the Docker/Airflow environment instead."
  exit 1
fi
EOF
