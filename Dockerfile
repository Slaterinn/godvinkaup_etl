##
#  This dockerfile is used for local development and testing
##
FROM apache/airflow:2.5.0

USER root

#RUN sudo apt-get update \
#    && apt-get install -y git --no-install-recommends \
#    gcc \
#    python3-distutils \
#    libpython3.9-dev


# Install git and other required packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    gcc \
    python3-distutils \
    libpython3.9-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create logs directory and set ownership
RUN mkdir -p /opt/airflow/dag_logs/dbt_logs && \
    chown -R airflow: /opt/airflow/dag_logs
ENV DBT_LOG_PATH=/opt/airflow/dag_logs/dbt_logs

# Create target dir and set ownership
RUN mkdir -p /opt/airflow/dag_logs/dbt_target \
    && chown -R airflow: /opt/airflow/dag_logs/dbt_target
ENV DBT_TARGET_PATH=/opt/airflow/dag_logs/dbt_target

# Create the custom dbt packages path and set permissions
#RUN mkdir -p /opt/airflow/godvinkaup_dbt/dbt_modules_custom && \
#    chown -R airflow: /opt/airflow/godvinkaup_dbt/dbt_modules_custom

USER airflow

#COPY --chown=airflow . .
COPY --chown=airflow godvinkaup_dbt /opt/airflow/godvinkaup_dbt
COPY --chown=airflow dags /opt/airflow/dags
COPY --chown=airflow plugins /opt/airflow/plugins
#COPY --chown=airflow requirements.txt /opt/airflow/requirements.txt


# We've had issues disabling poetry venv
# See: https://github.com/python-poetry/poetry/issues/1214
#RUN python -m pip install .
RUN pip install protobuf==3.20.3

# Setup dbt for the example project
RUN pip install dbt-postgres==1.5.9

#RUN dbt deps --project-dir /opt/airflow/example_dbt_project
