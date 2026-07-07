#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR="${RUNTIME_DIR:-$HOME/docker/dbt-airflow}"

echo "Syncing runtime repo: $RUNTIME_DIR"

cd "$RUNTIME_DIR"

if [ -n "$(git status --porcelain)" ]; then
  echo "Runtime repo has local changes. Commit, stash, or discard them before syncing."
  git status --short
  exit 1
fi

git checkout main
git pull origin main

echo "Runtime repo synced."
