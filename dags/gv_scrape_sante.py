from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from scripts.scrape_sante_filters import run as scrape_sante_filters
from scripts.scrape_sante_wines import run as scrape_sante_wines

default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "godvinkaup_extract_sante",
    default_args=default_args,
    description="Run Sante wine scraping scripts",
    schedule_interval="0 10 * * *",  # daily at 10:00
    catchup=False,
    tags=["godvinkaup", "extracts", "store_sante"],
) as dag:
    scrape_sante_filters = PythonOperator(
        task_id="scrape_sante_filters",
        python_callable=scrape_sante_filters,
        execution_timeout=timedelta(minutes=2),
    )

    scrape_sante_wines = PythonOperator(
        task_id="scrape_sante_wines",
        python_callable=scrape_sante_wines,
        execution_timeout=timedelta(minutes=2),
    )

    scrape_sante_filters >> scrape_sante_wines
