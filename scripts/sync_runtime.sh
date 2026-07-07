cat > scripts/sync_runtime.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR="${RUNTIME_DIR:-$HOME/docker/dbt-airflow}"

cd "$RUNTIME_DIR"

echo "Checking runtime git status..."
git status --short

if [ -n "$(git status --porcelain)" ]; then
  echo "Runtime repo has local changes. Commit, stash, or discard them before syncing."
  exit 1
fi

git checkout main
git pull origin main
EOF
