select
    player_id,
    player_name,
    team_short,
    case when position = 'D,M' then 'D'
	when position = 'M,F' then 'F'
	else position end as position,
    event_id,
    date,
    fantasy_points::numeric as fantasy_points,
    stats_json::jsonb as stats_json
from {{ source('landing', 'fantrax_player_scoring') }}
