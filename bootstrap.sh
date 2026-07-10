#!/usr/bin/env bash

set -e

echo "Bootstrapping Godvinkaup ETL..."

echo
echo "Checking uv..."
command -v uv >/dev/null || {
    echo "uv is not installed."
    exit 1
}

echo "Checking Ruff..."
command -v ruff >/dev/null || uv tool install ruff

echo "Checking pre-commit..."
command -v pre-commit >/dev/null || uv tool install pre-commit

echo "Installing Git hooks..."
pre-commit install

echo "Making scripts executable..."
chmod +x scripts/*.sh

echo "Checking dbt profile..."
if [ ! -f "$HOME/.dbt/profiles.yml" ]; then
    echo
    echo "Missing ~/.dbt/profiles.yml"
    echo "Create it before running dbt."
fi

echo
echo "Running workstation checks..."
make doctor

echo
echo "Bootstrap complete."
