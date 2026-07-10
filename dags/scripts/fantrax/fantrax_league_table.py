import requests
from airflow.providers.postgres.hooks.postgres import PostgresHook


def load_fantrax_league_table():
    hook = PostgresHook(postgres_conn_id="postgres_godvinkaup")
    conn = hook.get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS landing.fantrax_league_table (
            position        INTEGER,
            team            TEXT,
            games_played    INTEGER,
            points          INTEGER,
            goals_for       INTEGER,
            goals_against   INTEGER
        );
        TRUNCATE TABLE landing.fantrax_league_table;
    """)

    resp = requests.get("https://www.fotmob.com/api/tltable", params={"leagueId": "47"})
    data = resp.json()[0]["data"]["table"]["all"]

    rows = []
    for t in data:
        gf, ga = t["scoresStr"].split("-")
        rows.append((t["idx"], t["name"], t["played"], t["pts"], int(gf), int(ga)))

    cur.executemany(
        """
        INSERT INTO landing.fantrax_league_table
        VALUES (%s, %s, %s, %s, %s, %s)
    """,
        rows,
    )

    conn.commit()
