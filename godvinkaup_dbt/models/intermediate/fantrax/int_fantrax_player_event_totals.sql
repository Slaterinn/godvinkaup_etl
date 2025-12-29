select
    player_id,
    scoring_position,
    team_short,
    event_id,
    event_date,

    sum(points) as fantasy_points,

    sum(points) filter (where is_base_stat) as base_points,
    sum(points) filter(where not is_base_stat) as event_points,

    max(minutes_played) as minutes_played,
    max(player_gw_status) as service_status

from {{ ref('int_fantrax_scored_events') }}

group by
    player_id,
    scoring_position,
    team_short,
    event_id,
    event_date
