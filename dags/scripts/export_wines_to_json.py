# export_wines_to_json.py

import json

from airflow.providers.postgres.hooks.postgres import PostgresHook


def run():
    # Use the Airflow connection ID to get credentials
    pg_hook = PostgresHook(postgres_conn_id="postgres_godvinkaup")
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    query = """SELECT * FROM marts.wines WHERE rating > 3.4"""

    cursor.execute(query)
    rows = cursor.fetchall()
    colnames = [desc[0] for desc in cursor.description]
    result = [dict(zip(colnames, row)) for row in rows]

    def default_json(t):
        return str(t)

    json_object = json.dumps(result, default=default_json, indent=2)

    output_path = "/opt/airflow/godvinkaup_website/data/wines_json.json"
    with open(output_path, "w") as outfile:
        outfile.write(json_object)

    cursor.close()
    conn.close()
