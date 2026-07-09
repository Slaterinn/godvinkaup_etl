import json
import logging
import re

import requests
from airflow.hooks.postgres_hook import PostgresHook

LEAGUE_ID = "41hpiiy9mbujpnmu"
FANTRAX_URL = "https://www.fantrax.com/fxpa/req"


def parse_next_opponent(raw_text: str):
    """
    Extract opponent team code and home/away from Fantrax fixture text.
    Handles cases like:
      'BHA Sat 3:00PM'
      '@BRF Sat 3:00PM'
      'NEW 0 @MUN 1 F'
    """
    if not raw_text:
        return None, None

    # Find all 2–4 letter uppercase tokens (team codes)
    teams = re.findall(r"\b[A-Z]{2,4}\b", raw_text)

    if not teams:
        return None, None

    # Home/away: away if '@' appears anywhere
    home_away = "A" if "@" in raw_text else "H"

    # First team token is always the player's team opponent
    opponent = teams[0]

    return opponent, home_away


def load_fantrax_players(cookies: dict, headers: dict) -> None:
    log = logging.getLogger(__name__)

    payload = {
        "msgs": [
            {
                "method": "getPlayerStats",
                "data": {
                    "leagueId": LEAGUE_ID,
                    "statusOrTeamFilter": "ALL",
                    "pageNumber": "1",
                    "positionOrGroup": "SOCCER_NON_GOALIE",
                    "miscDisplayType": "1",
                    "maxResultsPerPage": "1000",
                },
            }
        ],
        "uiv": 3,
        "refUrl": f"https://www.fantrax.com/fantasy/league/{LEAGUE_ID}/players",
        "dt": 0,
        "at": 0,
        "av": "0.0",
        "tz": "Atlantic/Reykjavik",
        "v": "177.2.1",
    }

    resp = requests.post(
        FANTRAX_URL,
        params={"leagueId": LEAGUE_ID},
        cookies=cookies,
        headers=headers,
        data=json.dumps(payload),
        timeout=30,
    )

    data = resp.json()

    if "pageError" in data:
        raise ValueError(f"Fantrax error: {data['pageError']}")

    table = data["responses"][0]["data"]["statsTable"]
    log.info("Fetched %s players", len(table))

    pg = PostgresHook(postgres_conn_id="postgres_godvinkaup")
    conn = pg.get_conn()
    cur = conn.cursor()

    cur.execute("TRUNCATE TABLE landing.fantrax_player_list")

    insert_sql = """
        INSERT INTO landing.fantrax_player_list (
            player_id,
            player_name,
            team,
            position,
            next_event_id,
            next_opponent,
            next_home_away,
            next_fixture_text,
            roster_status_code,
            roster_status_label
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    for row in table:
        scorer = row["scorer"]
        cells = row.get("cells", [])

        # -------------------------
        # Upcoming fixture parsing
        # -------------------------
        next_event_id = None
        next_opponent = None
        next_home_away = None
        next_fixture_text = None

        if len(cells) > 2 and cells[2].get("content"):
            fixture_cell = cells[2]
            raw = fixture_cell["content"]

            # Preserve original text (for debugging / UI)
            next_fixture_text = raw.replace("<br/>", " ")

            # Event id (safe)
            next_event_id = fixture_cell.get("eventId")

            # NEW: robust parsing
            next_opponent, next_home_away = parse_next_opponent(raw)

        # -------------------------
        # Status of players
        # -------------------------
        status_cell = cells[1] if len(cells) > 1 else {}
        roster_status_code = status_cell.get("content")
        roster_status_label = status_cell.get("toolTip")

        cur.execute(
            insert_sql,
            (
                scorer["scorerId"],
                scorer["name"],
                scorer["teamShortName"],
                scorer["posShortNames"],
                next_event_id,
                next_opponent,
                next_home_away,
                next_fixture_text,
                roster_status_code,
                roster_status_label,
            ),
        )

    conn.commit()
    cur.close()
    conn.close()

    log.info("Fantrax player list load complete")
