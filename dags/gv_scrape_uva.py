from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow.utils.dates import days_ago
from scripts.scrape_uva_wines import run as scrape_uva_wines

default_args = {
    'owner': 'airflow',
    'start_date': days_ago(1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'godvinkaup_extract_uva',
    default_args=default_args,
    description='Run Uva wine scraping scripts',
    schedule_interval='0 10 * * *',  # daily at 10:00
    catchup=False,
    tags=['godvinkaup', 'extracts', 'store_uva'],
) as dag:


    scrape_uva_wines = PythonOperator(
        task_id='scrape_uva_wines',
        python_callable=scrape_uva_wines,
        execution_timeout=timedelta(minutes=2)
    )


    scrape_uva_wines
