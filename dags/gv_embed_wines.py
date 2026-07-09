from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from scripts.embed_wines import run as embed_wines

default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "godvinkaup_embed_wines",
    default_args=default_args,
    description="embeds wines with openai api and stores in qdrant cloud",
    schedule_interval="0 12 * * *",  # daily at 12:00
    catchup=False,
    tags=["godvinkaup", "embeddings"],
) as dag:
    embed_wines = PythonOperator(
        task_id="embed_wines", python_callable=embed_wines, execution_timeout=timedelta(minutes=2)
    )

    embed_wines
