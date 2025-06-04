# Define the default arguments for the DAG
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import datetime, timedelta

# Define the default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}
# Create the DAG with the specified schedule interval
dag = DAG('test_dbt_simple_dag', default_args=default_args, schedule_interval=None)
# Define dbt tasks using BashOperator
task1 = BashOperator(
    task_id='dbt_task1',
    bash_command='dbt run --profiles-dir /opt/airflow/.dbt --project-dir /opt/airflow/example_dbt_project',
    dag=dag
)
task2 = BashOperator(
    task_id='dbt_task2',
    bash_command='dbt test --profiles-dir /opt/airflow/.dbt --project-dir /opt/airflow/example_dbt_project',
    dag=dag
)
# Set task dependencies
task1 >> task2
