
with scored_stats as (

    select
        player_id,
        event_id,
	team_short,
	date as event_date,
        stat_key,
        stat_value,
	is_base_stat,
        points,
        position
    from {{ ref('int_fantrax_tiered_points') }}

),

minutes as (

    select
        player_id,
        event_id,
        minutes_played
    from {{ ref('stg_fantrax_player_minutes') }}

),

service as (

    select
        player_id,
        gameweek,
        owner,
	status,
        position as fantasy_position,
        gw_start_date,
        gw_end_date
    from {{ ref('stg_fantrax_player_service') }}

)
select
    ss.player_id,
    ss.event_id,
    ss.team_short,
    s.gameweek,
    ss.event_date,

    ss.stat_key,
    ss.stat_value,
    ss.points,
    ss.is_base_stat,

    ss.position as scoring_position,
    s.fantasy_position,

    m.minutes_played,

    s.owner as fantasy_owner,
    s.status as player_gw_status

from scored_stats ss

left join minutes m
    on ss.player_id = m.player_id
   and ss.event_id  = m.event_id

left join service s
    on ss.player_id = s.player_id
   and ss.event_date between s.gw_start_date and s.gw_end_date
