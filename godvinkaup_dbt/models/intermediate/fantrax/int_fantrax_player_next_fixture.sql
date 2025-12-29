select
    player_id,
    next_event_id as event_id,
    next_opponent as opponent,
    next_home_away,
    next_fixture_text

from {{ ref('stg_fantrax_player_list') }}
where next_event_id is not null
