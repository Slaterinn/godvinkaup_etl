select
    player_id,
    event_id,
    minutes_played::int as minutes_played
from {{ source('landing', 'fantrax_player_minutes') }}
