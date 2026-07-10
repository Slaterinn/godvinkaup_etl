import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import requests
from airflow.hooks.postgres_hook import PostgresHook

log = logging.getLogger(__name__)

FANTRAX_URL = "https://www.fantrax.com/fxpa/req"
LEAGUE_ID = "41hpiiy9mbujpnmu"

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

SEASON_START_YEAR = 2025  # for season 2025_26


# --------------------------------------------------
# Turn date text from fantrax into date
# --------------------------------------------------
def parse_fantrax_date(date_str: str) -> date | None:
    """
    Convert 'Dec 17' or 'Jan 14' → proper date.
    """
    if not date_str:
        return None

    try:
        month_str, day_str = date_str.split()
        month = MONTH_MAP[month_str]
        day = int(day_str)

        # Aug–Dec = season start year, Jan–Jul = next year
        year = SEASON_START_YEAR if month >= 8 else SEASON_START_YEAR + 1

        return date(year, month, day)

    except Exception:
        return None


# --------------------------------------------------
# Fetch one player's fantasy game log
# --------------------------------------------------
def fetch_player_scores(player, cookies, headers):
    player_id = player["player_id"]

    params = {"leagueId": LEAGUE_ID}

    payload = {
        "msgs": [
            {
                "method": "getPlayerProfile",
                "data": {"playerId": player_id, "tab": "GAME_LOG_FANTASY", "showDidNotPlays": True},
            }
        ],
        "uiv": 3,
        "refUrl": (
            "https://www.fantrax.com/fantasy/league/"
            f"{LEAGUE_ID}/players;"
            "positionOrGroup=SOCCER_NON_GOALIE;"
            "miscDisplayType=1;"
            "pageNumber=1"
        ),
        "dt": 0,
        "at": 0,
        "av": "0.0",
        "tz": "Atlantic/Reykjavik",
        "v": "177.2.1",
    }

    resp = requests.post(
        FANTRAX_URL,
        params=params,
        cookies=cookies,
        headers=headers,
        data=json.dumps(payload),
        timeout=30,
    )

    data = resp.json()

    # ------------------------------
    # Hard failure checks
    # ------------------------------
    if "pageError" in data:
        raise ValueError(data["pageError"])

    responses = data.get("responses", [])
    if not responses:
        return []

    section = responses[0]["data"].get("sectionContent")
    if not section or "GAME_LOG_FANTASY" not in section:
        return []

    table = section["GAME_LOG_FANTASY"]["tables"][0]

    # ------------------------------
    # Extract headers
    # ------------------------------
    headers_cells = table["header"]["cells"]
    stat_headers = [cell.get("shortName") or cell.get("name") for cell in headers_cells]

    rows_out = []

    for row in table["rows"]:
        stats = {}

        for header, cell in zip(stat_headers, row["cells"]):
            value = cell.get("content")
            if value == "":
                value = None
            stats[header] = value

        # Correctly extract event_id from cell index 3
        event_id = row["cells"][3]["props"].get("eventId")
        raw_date = row["cells"][0]["content"]
        match_date = parse_fantrax_date(raw_date)

        rows_out.append(
            {
                "player_id": player["player_id"],
                "player_name": player["player_name"],
                "team_short": player["team"],
                "position": player["position"],
                "event_id": event_id,  # updated line
                "date": match_date,
                "fantasy_points": stats.get("FPts"),
                "stats_json": json.dumps(stats),
            }
        )

    return rows_out


# --------------------------------------------------
# Main Airflow entrypoint
# --------------------------------------------------
def load_fantrax_player_scores(cookies, headers):
    hook = PostgresHook(postgres_conn_id="postgres_godvinkaup")
    conn = hook.get_conn()
    cur = conn.cursor()

    # --------------------------------------------------
    # Fetch players (non-goalies already filtered upstream)
    # --------------------------------------------------
    cur.execute("""
        SELECT
            player_id,
            player_name,
            team,
            position
        FROM landing.fantrax_player_list
    """)

    players = [
        {"player_id": r[0], "player_name": r[1], "team": r[2], "position": r[3]}
        for r in cur.fetchall()
    ]

    log.info(f"Fetched {len(players)} players")

    all_rows = []

    # Before parallel fetch
    cur.execute("TRUNCATE TABLE landing.fantrax_player_scoring")
    conn.commit()
    log.info("Truncated fantrax_player_scoring table")

    # --------------------------------------------------
    # Parallel fetch
    # --------------------------------------------------
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_player_scores, p, cookies, headers) for p in players]

        for future in as_completed(futures):
            try:
                rows = future.result()
                all_rows.extend(rows)
            except Exception as e:
                log.error(f"Player fetch failed: {e}")

    log.info(f"Inserting {len(all_rows)} scoring rows")

    if not all_rows:
        return

    insert_sql = """
        INSERT INTO landing.fantrax_player_scoring (
            player_id,
            player_name,
            team_short,
            position,
            event_id,
            date,
            fantasy_points,
            stats_json
        )
        VALUES (%(player_id)s, %(player_name)s, %(team_short)s,
                %(position)s, %(event_id)s, %(date)s,
                %(fantasy_points)s, %(stats_json)s)
    """

    cur.executemany(insert_sql, all_rows)
    conn.commit()

    log.info("Fantrax player scoring load complete")
