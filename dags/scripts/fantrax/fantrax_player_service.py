# fantrax_player_service.py
import datetime
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from airflow.hooks.postgres_hook import PostgresHook

log = logging.getLogger(__name__)

FANTRAX_URL = "https://www.fantrax.com/fxpa/req"
LEAGUE_ID = "41hpiiy9mbujpnmu"
WORKERS = 10
REQUEST_RETRIES = 3
REQUEST_BACKOFF = 1.0  # seconds


# --------------------------------------------------
# Utilities: parse gameweek date range
# --------------------------------------------------
MONTH_MAP = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def parse_date_range(gw_text):
    """
    Input: "1 (Aug 15 - Aug 21)"
    Output: (start_date, end_date)
    """
    try:
        inside = gw_text[gw_text.find("(") + 1 : gw_text.rfind(")")]
        start_str, end_str = [s.strip() for s in inside.split(" - ", 1)]
        sm, sd = start_str.split(" ")
        em, ed = end_str.split(" ")

        smn, sdn = MONTH_MAP[sm], int(sd)
        emn, edn = MONTH_MAP[em], int(ed)

        syear = 2025 if smn <= 6 else 2025
        eyear = 2025 if emn <= 6 else 2025

        return (datetime.date(syear, smn, sdn), datetime.date(eyear, emn, edn))
    except Exception:
        today = datetime.date.today()
        return today, today


# --------------------------------------------------
# Fetch one player's TEAM_SERVICE_TIME
# --------------------------------------------------
def fetch_player_service(player_id, cookies, headers):
    params = {"leagueId": LEAGUE_ID}

    payload = {
        "msgs": [
            {
                "method": "getPlayerProfile",
                "data": {"playerId": player_id, "tab": "TEAM_SERVICE_TIME"},
            }
        ],
        "uiv": 3,
        "refUrl": f"https://www.fantrax.com/fantasy/league/{LEAGUE_ID}/players",
        "dt": 0,
        "at": 0,
        "av": "3.0",
        "tz": "Atlantic/Reykjavik",
        "v": "177.2.1",
    }

    last_exc = None

    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            resp = requests.post(
                FANTRAX_URL,
                params=params,
                headers=headers,
                cookies=cookies,
                data=json.dumps(payload),
                timeout=30,
            )
            resp.raise_for_status()

            data = resp.json()

            rows = data["responses"][0]["data"]["sectionContent"]["TEAM_SERVICE_TIME"]["tables"][0][
                "rows"
            ]

            out = []

            for r in rows:
                cells = r.get("cells", [])
                if len(cells) < 4:
                    continue

                gw_text = cells[0].get("content", "")
                try:
                    gameweek = int(gw_text.split(" ")[0])
                except Exception:
                    continue

                gw_start, gw_end = parse_date_range(gw_text)

                try:
                    owner = cells[1]["props"]["teamInfoList"][0]["name"]
                except Exception:
                    owner = ""

                status = cells[2].get("content")
                position = cells[3].get("content")

                out.append(
                    {
                        "player_id": player_id,
                        "gameweek": gameweek,
                        "owner": owner,
                        "status": status,
                        "position": position,
                        "gw_start_date": gw_start,
                        "gw_end_date": gw_end,
                    }
                )

            return out

        except Exception as exc:
            last_exc = exc
            time.sleep(REQUEST_BACKOFF * (2 ** (attempt - 1)))

    raise last_exc


# --------------------------------------------------
# Main Airflow entrypoint
# --------------------------------------------------
def load_fantrax_player_service(cookies, headers):
    hook = PostgresHook(postgres_conn_id="postgres_godvinkaup")
    conn = hook.get_conn()
    cur = conn.cursor()

    # --------------------------------------------------
    # Truncate table
    # --------------------------------------------------
    cur.execute("TRUNCATE TABLE landing.fantrax_player_service")
    conn.commit()
    log.info("Truncated landing.fantrax_player_service")

    # --------------------------------------------------
    # Fetch players
    # --------------------------------------------------
    cur.execute("""
        SELECT player_id
        FROM landing.fantrax_player_list
    """)
    players = [r[0] for r in cur.fetchall()]
    log.info(f"Fetched {len(players)} players")

    all_rows = []

    # --------------------------------------------------
    # Parallel fetch
    # --------------------------------------------------
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(fetch_player_service, pid, cookies, headers): pid for pid in players
        }

        for future in as_completed(futures):
            pid = futures[future]
            try:
                rows = future.result()
                if rows:
                    all_rows.extend(rows)
            except Exception as e:
                log.error(f"Player service fetch failed for {pid}: {e}")

    log.info(f"Inserting {len(all_rows)} player service rows")

    if not all_rows:
        return

    insert_sql = """
        INSERT INTO landing.fantrax_player_service (
            player_id,
            gameweek,
            owner,
            status,
            position,
            gw_start_date,
            gw_end_date
        )
        VALUES (
            %(player_id)s,
            %(gameweek)s,
            %(owner)s,
            %(status)s,
            %(position)s,
            %(gw_start_date)s,
            %(gw_end_date)s
        )
    """

    cur.executemany(insert_sql, all_rows)
    conn.commit()
    log.info("Fantrax player service load complete")
