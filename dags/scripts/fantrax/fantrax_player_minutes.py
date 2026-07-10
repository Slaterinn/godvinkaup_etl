# fantrax_player_minutes.py
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from airflow.hooks.postgres_hook import PostgresHook

log = logging.getLogger(__name__)

FANTRAX_URL = "https://www.fantrax.com/fxpa/req"
LEAGUE_ID = "41hpiiy9mbujpnmu"
MAX_WORKERS = 10


# --------------------------------------------------
# Fetch one player's minutes
# --------------------------------------------------
def fetch_player_minutes(player_id, cookies, headers):
    params = {"leagueId": LEAGUE_ID}
    payload = {
        "msgs": [
            {"method": "getPlayerProfile", "data": {"playerId": player_id, "tab": "GAME_LOG"}}
        ],
        "uiv": 3,
        "refUrl": f"https://www.fantrax.com/fantasy/league/{LEAGUE_ID}/players",
        "dt": 0,
        "at": 0,
        "av": "0.0",
        "tz": "Atlantic/Reykjavik",
        "v": "177.2.1",
    }

    try:
        resp = requests.post(
            FANTRAX_URL,
            params=params,
            cookies=cookies,
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        rows = data["responses"][0]["data"]["sectionContent"]["GAME_LOG"]["tables"][0]["rows"]
        results = []

        for row in rows:
            cells = row.get("cells", [])
            event_id = cells[3].get("props", {}).get("eventId", None) if len(cells) > 3 else None

            try:
                minutes = float(cells[6].get("content", 0)) if len(cells) > 6 else 0
            except (ValueError, TypeError):
                minutes = 0

            results.append(
                {"player_id": player_id, "event_id": event_id, "minutes_played": minutes}
            )

        return results

    except Exception as e:
        log.error(f"Failed fetching minutes for player {player_id}: {e}")
        return []


# --------------------------------------------------
# Main Airflow entrypoint
# --------------------------------------------------
def load_fantrax_player_minutes(cookies, headers):
    hook = PostgresHook(postgres_conn_id="postgres_godvinkaup")
    conn = hook.get_conn()
    cur = conn.cursor()

    # Fetch players
    cur.execute("""
        SELECT player_id FROM landing.fantrax_player_list
    """)
    players = [r[0] for r in cur.fetchall()]
    log.info(f"Fetched {len(players)} players")

    # Optional: truncate table
    cur.execute("TRUNCATE TABLE landing.fantrax_player_minutes")
    conn.commit()
    log.info("Truncated fantrax_player_minutes table")

    all_rows = []

    # --------------------------------------------------
    # Parallel fetch
    # --------------------------------------------------
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_player_minutes, pid, cookies, headers): pid for pid in players
        }
        for future in as_completed(futures):
            pid = futures[future]
            try:
                rows = future.result()
                if rows:
                    all_rows.extend(rows)
            except Exception as e:
                log.error(f"Error fetching player {pid}: {e}")

    log.info(f"Inserting {len(all_rows)} player minutes rows")

    if not all_rows:
        return

    insert_sql = """
        INSERT INTO landing.fantrax_player_minutes(player_id, event_id, minutes_played)
        VALUES (%(player_id)s, %(event_id)s, %(minutes_played)s)
    """
    cur.executemany(insert_sql, all_rows)
    conn.commit()
    log.info("Fantrax player minutes load complete")
