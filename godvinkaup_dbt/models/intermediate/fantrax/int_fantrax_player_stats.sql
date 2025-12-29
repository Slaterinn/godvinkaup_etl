with base as (

    select
        player_id,
        player_name,
        team_short,
        position,
        event_id,
	date,
        stats_json
    from {{ ref('stg_fantrax_player_scoring') }}

),

exploded as (

    select
        player_id,
        player_name,
        team_short,
        position,
        event_id,
	date,
        key   as stat_key,
        value as stat_value_raw
    from base,
         jsonb_each_text(stats_json)

),

typed as (

    select
        player_id,
        player_name,
        team_short,
        position,
        event_id,
	date,
        stat_key,
        nullif(stat_value_raw, '')::numeric as stat_value
    from exploded
    where stat_key not in (
        'Opp',
        'Date',
        'Team',
        'Score',
        'FPts'
    )

)

select *
from typed
where stat_value is not null
