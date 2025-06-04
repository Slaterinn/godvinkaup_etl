from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.python import PythonSensor
from airflow.models import DagRun
from airflow.utils.state import State
from airflow.utils.dates import days_ago
from airflow.utils.timezone import make_naive
from datetime import timedelta
import pendulum

default_args = {
    'owner': 'airflow',
    'start_date': days_ago(1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def has_dag_succeeded_today(dag_id, **context):
    logical_date = context["data_interval_start"].date()  # Airflow's scheduled run date
    dag_runs = DagRun.find(dag_id=dag_id, state=State.SUCCESS)

    for run in dag_runs:
        if run.execution_date.date() == logical_date:
            return True
    return False


with DAG(
    dag_id='godvinkaup_dbt_run',
    default_args=default_args,
    schedule_interval='15 10 * * *',  # Daily at 10:15
    catchup=False,
    tags=['godvinkaup', 'dbt', 'union'],
) as dag:

    wait_for_atvr = PythonSensor(
        task_id='wait_for_atvr_extract',
        python_callable=has_dag_succeeded_today,
        op_kwargs={'dag_id': 'godvinkaup_extract_atvr'},
        poke_interval=30,
        timeout=3600,
        mode='poke',
    )

    wait_for_sante = PythonSensor(
        task_id='wait_for_sante_extract',
        python_callable=has_dag_succeeded_today,
        op_kwargs={'dag_id': 'godvinkaup_extract_sante'},
        poke_interval=30,
        timeout=3600,
        mode='poke',
    )

    wait_for_uva = PythonSensor(
        task_id='wait_for_uva_extract',
        python_callable=has_dag_succeeded_today,
        op_kwargs={'dag_id': 'godvinkaup_extract_uva'},
        poke_interval=30,
        timeout=3600,
        mode='poke',
    )

    dbt_run = BashOperator(
        task_id='GodVinkaup_dbt_run',
        bash_command="""
        cd /opt/airflow/godvinkaup_dbt && \
        dbt run --profiles-dir /opt/airflow/.dbt
        """
    )

    # Set dependencies
    [wait_for_atvr, wait_for_sante, wait_for_uva] >> dbt_run
