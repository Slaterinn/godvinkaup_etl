from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from scripts.export_wines_to_json import run as export_json_func
from scripts.push_gv_to_github import run as push_to_git

default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "export_wines_to_json",
    schedule_interval="0 12 * * *",  # daily at 12:00
    catchup=False,
    default_args=default_args,
    description="Export wine JSON and push to GitHub",
    tags=["godvinkaup", "export", "git push"],
) as dag:
    export_json = PythonOperator(
        task_id="export_json",
        python_callable=export_json_func,
    )

    git_push = PythonOperator(task_id="push_to_github", python_callable=push_to_git)

    export_json >> git_push
