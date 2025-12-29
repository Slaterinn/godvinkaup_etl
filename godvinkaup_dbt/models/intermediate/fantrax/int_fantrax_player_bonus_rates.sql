with events as (

    select
        player_id,
        scoring_position,
        event_id,
        event_date,

        stat_key,
        stat_value::numeric as stat_value,
        minutes_played

    from {{ ref('int_fantrax_scored_events') }}
    where stat_key in ('G', 'AT', 'CS')
),

aggregated as (

    select
        player_id,
        scoring_position,

        sum(case when stat_key = 'G'  then stat_value else 0 end) as goals,
        sum(case when stat_key = 'AT' then stat_value else 0 end) as assists,
        sum(case when stat_key = 'CS' then stat_value else 0 end) as clean_sheets,

        sum(minutes_played) as minutes_played

    from events
    group by 1,2
)

select
    player_id,
    scoring_position,

    goals,
    assists,
    clean_sheets,

    minutes_played,

    -- rates per 90
    goals * 90.0 / nullif(minutes_played, 0)        as goals_per_90,
    assists * 90.0 / nullif(minutes_played, 0)      as assists_per_90,
    clean_sheets * 90.0 / nullif(minutes_played, 0) as cs_per_90

from aggregated
