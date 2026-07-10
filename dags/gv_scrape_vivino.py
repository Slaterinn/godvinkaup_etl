from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from scripts.scrape_vivino_ratings import run as scrape_vivino_ratings

default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "godvinkaup_scrape_vivino",
    default_args=default_args,
    description="Run vivino ratings scraping scripts",
    schedule_interval="0 11 * * *",  # daily at 11:00
    catchup=False,
    tags=["godvinkaup", "vivino", "ratings"],
) as dag:
    scrape_uva_wines = PythonOperator(
        task_id="scrape_vivino_ratings",
        python_callable=scrape_vivino_ratings,
        execution_timeout=timedelta(minutes=2),
    )

    scrape_vivino_ratings
