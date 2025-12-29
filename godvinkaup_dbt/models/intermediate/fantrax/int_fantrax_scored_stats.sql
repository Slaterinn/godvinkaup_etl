with stats as (

    select
        player_id,
        player_name,
        team_short,
        position,
        event_id,
	date,
        stat_key,
        stat_value
    from {{ ref('int_fantrax_player_stats') }}

),

rules as (

    select
        position,
        stat_key,
        points_per_unit,
        is_positive,
        is_base_stat,
        season
    from {{ ref('stg_fantrax_scoring_rules') }}

),

scored as (

    select
        s.player_id,
        s.player_name,
        s.team_short,
        s.position,
        s.event_id,
	s.date,
        s.stat_key,
        s.stat_value,

        coalesce(r.points_per_unit,0) as points_per_unit,
        r.is_positive,
        coalesce(r.is_base_stat, true) as is_base_stat,

        -- raw stat contribution (no tiers yet)
        (s.stat_value * coalesce(r.points_per_unit,0))::numeric as raw_points

    from stats s
    left join rules r
      on s.stat_key = r.stat_key
     and s.position = r.position
     and r.season = '202526'

)

select *
from scored
