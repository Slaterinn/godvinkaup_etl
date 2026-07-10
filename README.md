# Godvinkaup ETL

Modern ETL platform powering the Godvinkaup data warehouse.

## Repository Layout

Development repository

~/projects/godvinkaup_etl

Runtime repository

~/docker/dbt-airflow

Development always happens in the development repository.

The runtime repository is synchronized only after validation.

## Quick Start

Clone the repository.

Run:

./bootstrap.sh

Verify the workstation:

make doctor

Validate the project:

make validate

## Common Commands

make doctor

make format

make lint

make validate

make sync-runtime

make deploy

## Documentation

See the docs directory for:

- setup
- deployment
- dbt
- airflow
- troubleshooting

## AI Development

AI agents should read AGENTS.md before making changes.
