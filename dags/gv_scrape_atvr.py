from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from scripts.fix_atvr_links import run as fix_atvr_links
from scripts.scrape_atvr_descriptions import run as scrape_descriptions
from scripts.scrape_red_wines import run as scrape_red_wines
from scripts.scrape_rose_wines import run as scrape_rose_wines
from scripts.scrape_sparkling_wines import run as scrape_sparkling_wines
from scripts.scrape_white_wines import run as scrape_white_wines

default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "godvinkaup_extract_atvr",
    default_args=default_args,
    description="Run ATVR wine scraping scripts",
    schedule_interval="0 10 * * *",  # daily at 10:00
    catchup=False,
    tags=["godvinkaup", "extracts", "store_atvr"],
) as dag:
    scrape_red = PythonOperator(
        task_id="scrape_red_wines",
        python_callable=scrape_red_wines,
        execution_timeout=timedelta(minutes=2),
    )

    scrape_white = PythonOperator(
        task_id="scrape_white_wines",
        python_callable=scrape_white_wines,
        execution_timeout=timedelta(minutes=2),
    )

    scrape_rose = PythonOperator(
        task_id="scrape_rose_wines",
        python_callable=scrape_rose_wines,
        execution_timeout=timedelta(minutes=2),
    )

    scrape_sparkling = PythonOperator(
        task_id="scrape_sparkling_wines",
        python_callable=scrape_sparkling_wines,
        execution_timeout=timedelta(minutes=2),
    )

    fix_links = PythonOperator(
        task_id="fix_atvr_links",
        python_callable=fix_atvr_links,
        execution_timeout=timedelta(minutes=2),
    )

    scrape_descriptions = PythonOperator(
        task_id="scrape_descriptions",
        python_callable=scrape_descriptions,
        execution_timeout=timedelta(minutes=2),
    )

    (
        scrape_red
        >> scrape_white
        >> scrape_rose
        >> scrape_sparkling
        >> fix_links
        >> scrape_descriptions
    )
