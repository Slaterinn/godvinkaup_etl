cat > scripts/deploy_to_runtime.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

"$SCRIPT_DIR/sync_runtime.sh"
"$SCRIPT_DIR/validate_airflow.sh"

echo "Deployment sync complete."
EOF
