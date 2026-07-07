"""
fantrax_player_news.py

Ingests:
- Player latestNews (analysisText, text) from:
  responses[i].data.sectionContent.OVERVIEW.latestNews

- Player injury messages from:
  responses[i].data.sectionContent.OVERVIEW.injuryInfo.injuryMsgs

Writes to Postgres (upsert) in:
  landing.fantrax_player_news

Airflow usage:
- Call run_fantrax_player_news_ingest(...) from a PythonOperator
- Pass league_id, cookies, headers
- postgres_conn_id defaults to "postgres_godvinkaup"
"""

import json
import re
import time
from html import unescape
from typing import Any, Dict, List, Optional, Tuple

import requests
from airflow.hooks.postgres_hook import PostgresHook


FANTRAX_REQ_URL = "https://www.fantrax.com/fxpa/req"

# Tune these as needed
BATCH_SIZE = 25
SLEEP_BETWEEN = 0.4
TIMEOUT = 30

# Destination table
DEST_TABLE = "landing.fantrax_player_news"

CREATE_TABLE_SQL = f"""
create schema if not exists landing;

create table if not exists {DEST_TABLE} (
    player_id           text primary key,
    analysis_text       text,
    news_text           text,
    news_updated_at     timestamptz null,
    raw_latest_news     jsonb,

    injury_msgs_raw     jsonb,
    injury_text         text,
    is_injured          boolean not null default false,

    source_event_date   date null,
    inserted_at         timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

create index if not exists ix_fantrax_player_news_updated_at
    on {DEST_TABLE}(updated_at);
"""

UPSERT_SQL = f"""
insert into {DEST_TABLE} (
    player_id,
    analysis_text,
    news_text,
    news_updated_at,
    raw_latest_news,
    injury_msgs_raw,
    injury_text,
    is_injured,
    source_event_date,
    updated_at
) values (
    %(player_id)s,
    %(analysis_text)s,
    %(news_text)s,
    %(news_updated_at)s,
    %(raw_latest_news)s::jsonb,
    %(injury_msgs_raw)s::jsonb,
    %(injury_text)s,
    %(is_injured)s,
    %(source_event_date)s,
    now()
)
on conflict (player_id) do update set
    analysis_text     = excluded.analysis_text,
    news_text         = excluded.news_text,
    news_updated_at   = excluded.news_updated_at,
    raw_latest_news   = excluded.raw_latest_news,
    injury_msgs_raw   = excluded.injury_msgs_raw,
    injury_text       = excluded.injury_text,
    is_injured        = excluded.is_injured,
    source_event_date = excluded.source_event_date,
    updated_at        = now();
"""


# -------------------------
# Helpers
# -------------------------

_TAG_RE = re.compile(r"<[^>]+>")

def strip_html(s: str) -> str:
    """Remove HTML tags and unescape entities."""
    return unescape(_TAG_RE.sub("", s)).strip()


def chunked(items: List[str], n: int) -> List[List[str]]:
    return [items[i:i + n] for i in range(0, len(items), n)]


def build_payload(player_ids: List[str], team_id: Optional[str] = None) -> str:
    """
    Fantrax expects JSON string with msgs[].
    Include teamId only if provided (some setups require it).
    """
    msgs = []
    for pid in player_ids:
        data_obj: Dict[str, Any] = {"playerId": pid}
        if team_id:
            data_obj["teamId"] = team_id

        msgs.append({"method": "getPlayerProfile", "data": data_obj})

    payload = {
        "msgs": msgs,
        "uiv": 3,
        "dt": 1,
        "at": 0,
        "av": "0.0",
        "tz": "Atlantic/Reykjavik",
        "v": "179.0.1",
    }
    return json.dumps(payload)


def fetch_fantasy_team_id(
    session: requests.Session,
    params: Dict[str, str],
    cookies: Dict[str, str],
    headers: Dict[str, str],
) -> Optional[str]:
    """
    Optional helper: getFantasyTeams once to retrieve a teamId, in case Fantrax
    requires teamId for getPlayerProfile in your league/session context.
    """
    data = json.dumps({
        "msgs": [{"method": "getFantasyTeams", "data": {}}],
        "uiv": 3,
        "dt": 1,
        "at": 0,
        "av": "0.0",
        "tz": "Atlantic/Reykjavik",
        "v": "179.0.1",
    })

    r = session.post(
        FANTRAX_REQ_URL,
        params=params,
        cookies=cookies,
        headers=headers,
        data=data,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    j = r.json()

    responses = j.get("responses", [])
    if not responses:
        return None

    teams_data = responses[0].get("data", {}) or {}

    # Common patterns: fantasyTeams[] or teams[]
    for key in ("fantasyTeams", "teams", "data"):
        val = teams_data.get(key)
        if isinstance(val, list) and val:
            for cand in ("teamId", "id"):
                if cand in val[0]:
                    return val[0][cand]
    return None


def extract_latest_news(profile_response: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str], Dict[str, Any]]:
    """
    Extract:
      data.sectionContent.OVERVIEW.latestNews.analysisText
      data.sectionContent.OVERVIEW.latestNews.text

    latestNews can be dict or list; we take the first element if list.
    """
    data = profile_response.get("data") or {}
    overview = (data.get("sectionContent") or {}).get("OVERVIEW") or {}
    latest_news = overview.get("latestNews")

    if not latest_news:
        return None, None, None, {}

    if isinstance(latest_news, list):
        latest = latest_news[0] if latest_news else {}
    elif isinstance(latest_news, dict):
        latest = latest_news
    else:
        latest = {}

    analysis_text = latest.get("analysisText")
    news_text = latest.get("text")

    # Optional timestamp keys (varies)
    news_updated_at = None
    for ts_key in ("updated", "updatedAt", "timestamp", "dateTime"):
        if latest.get(ts_key):
            news_updated_at = str(latest[ts_key])
            break

    return analysis_text, news_text, news_updated_at, latest


def extract_injury_info(profile_response: Dict[str, Any]) -> Tuple[bool, Optional[str], Any]:
    """
    Extract:
      data.sectionContent.OVERVIEW.injuryInfo.injuryMsgs

    Example:
      ["Expected to return on Sun Mar 1 - <i>Out for next game.</i>"]

    Returns:
      (is_injured, injury_text, injury_msgs_raw)
    """
    data = profile_response.get("data") or {}
    overview = (data.get("sectionContent") or {}).get("OVERVIEW") or {}
    injury_info = overview.get("injuryInfo") or {}
    injury_msgs = injury_info.get("injuryMsgs")

    if not injury_msgs:
        return False, None, None

    if isinstance(injury_msgs, list):
        cleaned = [strip_html(str(x)) for x in injury_msgs if x is not None]
        injury_text = " | ".join([c for c in cleaned if c]) if cleaned else None
        raw = injury_msgs
    else:
        injury_text = strip_html(str(injury_msgs))
        raw = injury_msgs

    # Conservative rule: any non-empty injury message => injured
    is_injured = True if injury_text else False
    return is_injured, injury_text, raw


def fetch_profiles_batch(
    session: requests.Session,
    params: Dict[str, str],
    cookies: Dict[str, str],
    headers: Dict[str, str],
    player_ids: List[str],
    team_id: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Fetch getPlayerProfile for a batch of player_ids; parse latestNews + injuryInfo.
    Returns dict keyed by player_id.
    """
    data = build_payload(player_ids, team_id=team_id)
    r = session.post(
        FANTRAX_REQ_URL,
        params=params,
        cookies=cookies,
        headers=headers,
        data=data,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    j = r.json()

    responses = j.get("responses", [])
    out: Dict[str, Dict[str, Any]] = {}

    # Typically responses align with msgs order; be defensive.
    for idx, pid in enumerate(player_ids):
        resp = responses[idx] if idx < len(responses) else {}

        analysis_text, news_text, news_updated_at, raw_latest = extract_latest_news(resp)
        is_injured, injury_text, injury_raw = extract_injury_info(resp)

        out[pid] = {
            "player_id": pid,
            "analysis_text": analysis_text,
            "news_text": news_text,
            "news_updated_at": news_updated_at,
            "raw_latest_news": json.dumps(raw_latest) if raw_latest else "{}",
            "injury_msgs_raw": json.dumps(injury_raw) if injury_raw else "{}",
            "injury_text": injury_text,
            "is_injured": is_injured,
        }

    return out


def ensure_table(pg: PostgresHook) -> None:
    """Create destination table if it does not exist."""
    pg.run(CREATE_TABLE_SQL)


def get_player_ids_from_db(pg: PostgresHook) -> List[str]:
    """
    Adjust this query to your actual player list source.

    Preferred: use whatever your existing pipeline already uses as the canonical player list.
    """
    sql = """
    select distinct player_id
    from landing.fantrax_player_list
    where player_id is not null
    """
    rows = pg.get_records(sql)
    return [r[0] for r in rows]


def upsert_rows(pg: PostgresHook, rows: List[Dict[str, Any]]) -> None:
    """Batch upsert into Postgres."""
    with pg.get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_SQL, rows)
        conn.commit()


# -------------------------
# Main entrypoint
# -------------------------

def run_fantrax_player_news_ingest(
    league_id: str,
    cookies: Dict[str, str],
    headers: Dict[str, str],
    postgres_conn_id: str = "postgres_godvinkaup",
) -> None:
    """
    Airflow callable.
    - league_id: Fantrax leagueId (e.g., '41hpiiy9mbujpnmu')
    - cookies/headers: authenticated session info (reuse your existing auth flow)
    - postgres_conn_id: Airflow connection id (default: postgres_godvinkaup)
    """
    pg = PostgresHook(postgres_conn_id=postgres_conn_id)
    ensure_table(pg)

    player_ids = get_player_ids_from_db(pg)
    if not player_ids:
        return

    params = {"leagueId": league_id}
    session = requests.Session()

    # Optional fallback teamId if Fantrax requires it
    team_id: Optional[str] = None
    try:
        team_id = fetch_fantasy_team_id(session, params, cookies, headers)
    except Exception:
        team_id = None

    buffer: List[Dict[str, Any]] = []

    for batch in chunked(player_ids, BATCH_SIZE):
        # First attempt without teamId; if it errors and we have teamId, retry.
        try:
            batch_out = fetch_profiles_batch(session, params, cookies, headers, batch, team_id=None)
        except requests.HTTPError:
            if team_id:
                batch_out = fetch_profiles_batch(session, params, cookies, headers, batch, team_id=team_id)
            else:
                raise

        for _, rec in batch_out.items():
            # Optional: set if you want to track "as of" date from another table
            rec["source_event_date"] = None

            # Ensure keys exist for upsert
            rec.setdefault("raw_latest_news", "{}")
            rec.setdefault("injury_msgs_raw", "{}")
            rec.setdefault("injury_text", None)
            rec.setdefault("is_injured", False)

            buffer.append(rec)

        # Flush periodically
        if len(buffer) >= 500:
            upsert_rows(pg, buffer)
            buffer = []

        time.sleep(SLEEP_BETWEEN)

    if buffer:
        upsert_rows(pg, buffer)
