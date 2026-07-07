#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

"$SCRIPT_DIR/sync_runtime.sh"
"$SCRIPT_DIR/validate_airflow.sh"
"$SCRIPT_DIR/validate_dbt.sh"

echo "Deployment validation complete."
