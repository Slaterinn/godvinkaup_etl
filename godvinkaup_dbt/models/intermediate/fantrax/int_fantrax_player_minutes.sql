
-- -------------------------------------------------
-- All events joined with players
-- -------------------------------------------------
with team_events as (
select
	  ec.event_id
	, ec.match_date as event_date
	, pl.player_id
	, pl.player_name
	, pl.team
from
	{{ ref('int_fantrax_event_context') }} ec
join 	{{ ref('stg_fantrax_player_list') }} pl on (ec.team = pl.team)
),

-- -------------------------------------------------
-- Get all minutes
-- -------------------------------------------------
player_minutes_full as (
select
	  te.player_id
	, te.player_name
	, te.event_id
	, te.event_date
	, coalesce(pet.minutes_played, 0) as minutes_played
from
team_events te
left join {{ ref('int_fantrax_player_event_totals') }} pet
	on  te.player_id = pet.player_id
	and te.event_id = pet.event_id
),

-- -------------------------------------------------
-- Rank events based on date
-- -------------------------------------------------
events_ordered as (
select
	  player_id
	, player_name
	, minutes_played
	, row_number() over (
		partition by player_id
		order by event_date desc
	  ) as rn
from player_minutes_full
),

-- -------------------------------------------------
-- Calculate average minutes per player
-- -------------------------------------------------
avg_minutes as (
select
	  player_id
	, avg(case when rn <= 5 then minutes_played end) as avg_minutes_last_5
	, avg(case when rn > 5 then minutes_played end) as avg_minutes_before
        , avg(minutes_played) as avg_minutes_total
from events_ordered
group by player_id
)

select
	  player_id
	, avg_minutes_last_5
	, avg_minutes_before
	, avg_minutes_total
	, round(avg_minutes_last_5) as expected_minutes
	, case
		when avg_minutes_last_5 >= 75 then 'starter'
		when avg_minutes_last_5 >= 40 then 'rotation'
	  	else 'bench'
	  end as role_label
	, case
		when avg_minutes_last_5 > avg_minutes_before + 5 then 'up'
		when avg_minutes_last_5 < avg_minutes_before -5 then 'down'
		else 'stable'
	  end as minutes_trend
from avg_minutes
