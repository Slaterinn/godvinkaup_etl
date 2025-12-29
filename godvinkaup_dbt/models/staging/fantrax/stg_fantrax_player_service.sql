select
    player_id,
    gameweek,
    owner,
    status,
    position,
    gw_start_date,
    gw_end_date
from {{ source('landing', 'fantrax_player_service') }}
