
with base as (

    select
        player_id,
        player_name,
        team_short,
        position,
        event_id,
	date,
        stat_key,
        stat_value,
        raw_points,
        is_base_stat
    from {{ ref('int_fantrax_scored_stats') }}

),

tiers as (

    select
        position,
        stat_key,
        min_value,
        max_value,
        step_size,
        points_per_step,
        season
    from {{ ref('stg_fantrax_scoring_tiers') }}
    where season = '202526'

),

tiered_calc as (

    select
        b.player_id,
        b.player_name,
        b.team_short,
        b.position,
        b.event_id,
	b.date,
        b.stat_key,
        b.stat_value,
        coalesce(b.is_base_stat,true) as is_base_stat,
	coalesce(b.raw_points,0) as raw_points,
        -- calculate tier contribution
        case
		  when stat_value < min_value then 0
		  else
		    floor( (stat_value - min_value) / step_size + 1 )
		    * points_per_step
		end as tier_points

    from base b
    left join tiers t
      on b.position = t.position
     and b.stat_key = t.stat_key

),

final as (

    select
        player_id,
        player_name,
        team_short,
        position,
        event_id,
	date,
        stat_key,
        stat_value,
        is_base_stat,

        -- if tiered exists, sum tiers; else use raw_points
        coalesce(sum(tier_points), max(raw_points))::numeric as points

    from tiered_calc
    group by
        player_id,
        player_name,
        team_short,
        position,
        event_id,
	date,
        stat_key,
        stat_value,
        is_base_stat

)

select *
from final
