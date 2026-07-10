SHELL := /bin/bash

.PHONY: help status git-check validate validate-airflow validate-dbt \
        sync-runtime deploy clean-pyc clean docs doctor

help:
	@echo "Godvinkaup ETL developer commands"
	@echo ""
	@echo "  make help              Show this help message"
	@echo "  make status            Show git status and current branch"
	@echo "  make git-check         Check branch and uncommitted changes"
	@echo "  make doctor            Check local development environment"
	@echo ""
	@echo "  make validate          Run all validation checks"
	@echo "  make validate-airflow  Run Airflow validation"
	@echo "  make validate-dbt      Run dbt validation"
	@echo ""
	@echo "  make sync-runtime      Sync development repo to runtime repo"
	@echo "  make deploy            Deploy latest validated changes to runtime"
	@echo ""
	@echo "  make clean-pyc         Remove Python cache files"
	@echo "  make clean             Remove generated/cache files"
	@echo "  make docs              List documentation files"

status:
	@git status --short
	@echo ""
	@echo "Branch:"
	@git branch --show-current

git-check:
	@echo "Current branch: $$(git branch --show-current)"
	@echo ""
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Working tree has changes:"; \
		git status --short; \
	else \
		echo "Working tree clean."; \
	fi

doctor:
	@echo "Checking development environment..."
	@echo ""
	@command -v git >/dev/null 2>&1 && echo "✅ git found" || echo "❌ git missing"
	@command -v docker >/dev/null 2>&1 && echo "✅ docker found" || echo "❌ docker missing"
	@docker info >/dev/null 2>&1 && echo "✅ docker daemon running" || echo "❌ docker daemon not running"
	@docker compose version >/dev/null 2>&1 && echo "✅ docker compose available" || echo "❌ docker compose missing"
	@command -v python3 >/dev/null 2>&1 && echo "✅ python3 found: $$(python3 --version)" || echo "❌ python3 missing"
	@command -v node >/dev/null 2>&1 && echo "✅ node found: $$(node --version)" || echo "❌ node missing"
	@command -v npm >/dev/null 2>&1 && echo "✅ npm found: $$(npm --version)" || echo "❌ npm missing"
	@command -v claude >/dev/null 2>&1 && echo "✅ Claude Code found" || echo "⚠️  Claude Code not found"
	@command -v codex >/dev/null 2>&1 && echo "✅ Codex CLI found" || echo "⚠️  Codex CLI not found"

	@echo ""
	@echo "Repository:"
	@echo "  Branch: $$(git branch --show-current)"
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "  Working tree: has changes"; \
		git status --short; \
	else \
		echo "  Working tree: clean"; \
	fi

	@echo ""
	@echo "Git remote:"
	@git ls-remote --heads origin >/dev/null 2>&1 && echo "✅ git remote reachable" || echo "❌ git remote not reachable"

	@echo ""
	@echo "GitHub SSH:"
	@ssh -T git@github.com 2>&1 | grep -q "successfully authenticated" \
		&& echo "✅ GitHub SSH authenticated" \
		|| echo "⚠️  GitHub SSH check did not confirm authentication"

	@echo ""
	@echo "Scripts:"
	@[ -x ./scripts/validate_airflow.sh ] && echo "✅ validate_airflow.sh executable" || echo "❌ validate_airflow.sh missing or not executable"
	@[ -x ./scripts/validate_dbt.sh ] && echo "✅ validate_dbt.sh executable" || echo "❌ validate_dbt.sh missing or not executable"
	@[ -x ./scripts/sync_runtime.sh ] && echo "✅ sync_runtime.sh executable" || echo "❌ sync_runtime.sh missing or not executable"
	@[ -x ./scripts/deploy_to_runtime.sh ] && echo "✅ deploy_to_runtime.sh executable" || echo "❌ deploy_to_runtime.sh missing or not executable"

	@echo ""
	@echo "dbt:"
	@[ -f $$HOME/.dbt/profiles.yml ] \
		&& echo "✅ dbt profile found: $$HOME/.dbt/profiles.yml" \
		|| echo "❌ dbt profile missing: $$HOME/.dbt/profiles.yml"
	@if [ -f $$HOME/.dbt/profiles.yml ] && grep -q "192\.168\.86\.23" $$HOME/.dbt/profiles.yml; then \
		echo "⚠️  old database IP still present in dbt profile"; \
	else \
		echo "✅ no old hardcoded dbt IP found"; \
	fi

	@echo ""
	@echo "Docker containers:"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || true

	@echo ""
	@echo "System resources:"
	@df -h / | tail -n 1 | awk '{print "Disk /: " $$4 " free of " $$2 " (" $$5 " used)"}'
	@free -h | awk '/Mem:/ {print "Memory: " $$7 " available of " $$2}'

validate: validate-airflow validate-dbt
	@echo ""
	@echo "✅ All validation completed."

validate-airflow:
	@./scripts/validate_airflow.sh

validate-dbt:
	@./scripts/validate_dbt.sh

sync-runtime:
	@./scripts/sync_runtime.sh

deploy:
	@./scripts/deploy_to_runtime.sh

clean-pyc:
	@find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@echo "Removed Python cache files."

clean: clean-pyc
	@echo "Clean completed."

docs:
	@find docs -maxdepth 2 -type f | sort

format:
	@echo "Formatting Python..."
	@ruff format .
	@ruff check . --select I --fix
	@echo "✅ Formatting complete."

lint:
	@echo "Linting Python..."
	@ruff check .
	@echo "✅ Lint completed."

bootstrap:
	@./bootstrap.sh
