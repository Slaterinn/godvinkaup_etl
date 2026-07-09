# AGENTS.md

# Godvinkaup ETL

## Purpose

This repository contains the ETL platform for Godvinkaup, a wine recommendation project focused on wines sold in Iceland.

The project consists primarily of:

- Airflow DAGs for orchestration
- dbt models for transformations
- Docker for the runtime environment

The objective is to build an ETL platform that is reliable, understandable, easy to maintain and safe to deploy.

---

# Architecture

High-level flow:

External Sources
        ↓
Extraction
        ↓
Airflow DAGs
        ↓
Raw / Staging Data
        ↓
dbt Transformations
        ↓
Business-ready datasets

Airflow is responsible for orchestration.

dbt is responsible for transformations.

Business logic should live in dbt whenever practical rather than inside Airflow DAGs.

---

# Repository Structure

dags/
: Airflow DAG definitions and orchestration code.

godvinkaup_dbt/
: dbt project.

docs/
: Human documentation.

Dockerfile

docker-compose.yml

: Development/runtime environment.

---

## Standard Development Commands

AI agents should use the Makefile as the primary interface to the repository.

Do **not** invoke helper scripts directly unless debugging those scripts.

Preferred commands:

| Task | Command |
|------|---------|
| Show available commands | `make help` |
| Verify workstation | `make doctor` |
| Validate project | `make validate` |
| Validate Airflow | `make validate-airflow` |
| Validate dbt | `make validate-dbt` |
| Sync runtime repository | `make sync-runtime` |
| Deploy | `make deploy` |
| Show repository status | `make status` |
| Check branch & changes | `make git-check` |
| Clean cache files | `make clean` |

---

# Development Workflow

Development always happens in:

```text
~/projects/godvinkaup_etl
```

GitHub is the source of truth.

The runtime Airflow environment is located in:

```text
~/docker/dbt-airflow
```

Airflow reads DAGs from:

```text
~/docker/dbt-airflow/dags
```

Never modify the runtime environment directly unless explicitly requested.

Normal workflow:

Development
        ↓
Feature Branch
        ↓
Review
        ↓
Commit
        ↓
Push to GitHub
        ↓
Pull into ~/docker/dbt-airflow
        ↓
Validate
        ↓
Production

---

# Git Workflow

Do not work directly on `main`.

Create a feature branch for each logical task.

Keep commits small and focused.

Write descriptive commit messages.

Never force-push unless explicitly requested.

---

# Coding Philosophy

Priorities, in order:

1. Correctness
2. Readability
3. Maintainability
4. Performance

Prefer explicit code over clever code.

Avoid unnecessary abstractions.

Avoid duplicate implementations.

Prefer extending existing patterns over introducing new ones.

Keep business logic easy to understand.

If a large refactor is proposed, explain why it is worthwhile before making it.

---

# Airflow Guidelines

Keep DAGs easy to read.

Avoid duplicated operators.

Avoid side effects during module import.

Do not change schedules, retries, dependencies or production behaviour unless explicitly requested.

Use reusable helper functions where appropriate.

Airflow should orchestrate work, not contain large amounts of business logic.

---

# dbt Guidelines

Prefer readable SQL.

Keep models modular.

Use descriptive model names.

Add tests where appropriate.

Consider downstream dependencies before renaming models.

Keep transformations in dbt rather than Python whenever practical.

---

# Python Guidelines

Use type hints where practical.

Prefer small functions.

Prefer composition over deeply nested logic.

Use logging instead of `print()`.

Handle errors explicitly.

Avoid global mutable state.

---

# Validation

Before considering work complete:

Review:

- `git status`
- `git diff`

Run relevant validation where practical.

## dbt

If dbt is available on the host:

```bash
cd godvinkaup_dbt
dbt parse
dbt compile
```

Otherwise, run the equivalent commands inside the Docker/Airflow environment.

## Airflow

Validate DAGs using the Airflow Docker environment whenever practical.

When changing DAGs, ensure they import successfully and do not introduce scheduling or dependency issues.

## General

If validation cannot be executed because the required environment is unavailable, clearly state that fact instead of claiming the change has been tested.

---

## Local Configuration

The dbt connection profile is intentionally not stored in Git.

Location:

    ~/.dbt/profiles.yml

If dbt cannot connect to the database, verify this file before debugging the project itself.

---

# AI Collaboration

Before making assumptions, ask if requirements are unclear.

Prefer small incremental improvements.

Explain potentially risky changes before applying them.

Do not silently introduce architectural changes.

Do not modify deployment scripts unless requested.

Do not modify the runtime deployment under `~/docker/dbt-airflow` unless explicitly instructed.

Preserve backwards compatibility whenever practical.

If multiple implementation options exist, explain the trade-offs and recommend one.

When reviewing code, explain both strengths and weaknesses.

If technical debt unrelated to the current task is discovered, mention it separately instead of changing it automatically.

---

# Things To Avoid

Do not introduce dependencies without a good reason.

Do not rewrite working code only for style.

Do not optimize prematurely.

Do not generate placeholder implementations unless requested.

Do not remove comments or documentation without reason.

---

# Long-term Goal

The objective is to evolve this repository into a reliable, production-quality ETL platform where both humans and AI agents can safely collaborate.

Every change should leave the codebase simpler, clearer and easier to maintain than before.
