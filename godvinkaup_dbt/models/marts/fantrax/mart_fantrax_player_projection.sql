
with base_events as (

    select
        player_id,
        scoring_position,
        team_short,
        event_id,
        event_date,
        fantasy_points,
	base_points,
	event_points,
        minutes_played
    from {{ ref('int_fantrax_player_event_totals') }}

),

-- -------------------------------------------------
-- Player baseline performance
-- -------------------------------------------------
player_baseline as (

    select
        player_id,
        scoring_position,
        team_short,

        count(*)                            as matches_played,
        avg(fantasy_points)                 as avg_fp,
	avg(base_points)		    as avg_base_fp,
	avg(event_points)		    as avg_bonus_fp,
        avg(minutes_played)                 as avg_minutes,

	stddev_samp(base_points)            as stdev_base_fp,

        case
            when sum(minutes_played) > 180
            then avg(fantasy_points) / avg(minutes_played) * 90
            else null
        end                                 as avg_fp_per_90,

        case
            when sum(minutes_played) > 180
            then avg(base_points) / avg(minutes_played) * 90
            else null
        end                              as avg_base_fp_per_90

    from base_events
    group by 1,2,3
),

-- -------------------------------------------------
-- Expected minutes (simple & explainable)
-- -------------------------------------------------
team_events as (

    select
        ec.event_id,
        ec.match_date as event_date,
        pl.player_id,
        pl.team
    from {{ ref('int_fantrax_event_context') }} ec
    join {{ ref('stg_fantrax_player_list') }} pl
      on pl.team = ec.team
),

player_minutes_full as (

    select
        te.player_id,
        te.event_id,
        te.event_date,
        coalesce(pet.minutes_played, 0) as minutes_played
    from team_events te
    left join {{ ref('int_fantrax_player_event_totals') }} pet
      on te.player_id = pet.player_id
     and te.event_id  = pet.event_id
),

recent_events as (

    select
        player_id,
        minutes_played,
        row_number() over (
            partition by player_id
            order by event_date desc
        ) as rn
    from player_minutes_full
),

recent_minutes as (

    select
        player_id,
        avg(minutes_played) as avg_minutes_last_5
    from recent_events
    where rn <= 5
    group by player_id
),

expected_minutes as (

    select
        player_id,
	avg_minutes_last_5,
        case
            when avg_minutes_last_5 >= 80 then 90
            when avg_minutes_last_5 >= 65 then 80
            when avg_minutes_last_5 >= 45 then 65
            when avg_minutes_last_5 >= 25 then 40
            when avg_minutes_last_5 >  10 then 20
            else 0
        end as expected_minutes

    from recent_minutes
),


-- -------------------------------------------------
-- Upcoming fixture context
-- -------------------------------------------------
upcoming_fixture as (

    select
        player_id,
        next_opponent        as opponent,
        next_home_away           as home_away
    from {{ ref('stg_fantrax_player_list') }}
),

-- -------------------------------------------------
-- Opponent strength adjustment
-- -------------------------------------------------
opponent_adjustment as (

    select
        scoring_position,
        opponent,
        avg_delta_vs_opponent
    from {{ ref('int_fantrax_team_strength') }}
),

-- -------------------------------------------------
-- Player availability
-- -------------------------------------------------
player_availability as (

    select
        player_id,
	player_name,
	roster_status_label,
        is_free_agent,
        is_waiver_wire,
        is_owned
    from {{ ref('int_fantrax_player_roster_status') }}

),

-- -------------------------------------------------
-- Expected clean sheets
-- -------------------------------------------------
expected_clean_sheets as (
    select
	team_short,
	opponent,
	home_away,
	team_ga_per_match,
	opp_gf_per_match,
	expected_goals_against,
	clean_sheet_probability,
	expected_cs_points
    from {{ ref('int_fantrax_expected_clean_sheet_next_fixture') }}
),

-- -------------------------------------------------
-- Opponent defensive context (stable, opponent-aware)
-- -------------------------------------------------
league_defense as (

    select
        avg(goals_against::numeric) as league_avg_ga
    from {{ ref('int_fantrax_event_context') }}

),

opponent_defense as (

    -- Treat "opponent" as a team; we want how many goals they concede on average
    select
        team as opponent,
        avg(goals_against::numeric) as opp_ga_per_match,
        count(*) as matches
    from {{ ref('int_fantrax_event_context') }}
    group by 1
),

-- -------------------------------------------------
-- Player goal/assist totals by event (from scored_events)
-- -------------------------------------------------
player_event_g_a as (

    select
        player_id,
        event_id,

        sum(case when stat_key = 'G'  then coalesce(stat_value::numeric, 0) else 0 end) as goals,
        sum(case when stat_key = 'AT' then coalesce(stat_value::numeric, 0) else 0 end) as assists

    from {{ ref('int_fantrax_scored_events') }}
    where stat_key in ('G','AT')
    group by 1,2
),

-- -------------------------------------------------
-- Player per-90 scoring rates (fantasy xG/xA basis)
-- -------------------------------------------------
player_rates as (

    select
        e.player_id,
        e.scoring_position,
        e.team_short,

        sum(coalesce(ga.goals, 0))   as total_goals,
        sum(coalesce(ga.assists, 0)) as total_assists,
        sum(coalesce(e.minutes_played, 0)) as total_minutes,

        case
            when sum(coalesce(e.minutes_played, 0)) > 0
            then sum(coalesce(ga.goals, 0)) / sum(e.minutes_played) * 90
            else 0
        end as goals_per90,

        case
            when sum(coalesce(e.minutes_played, 0)) > 0
            then sum(coalesce(ga.assists, 0)) / sum(e.minutes_played) * 90
            else 0
        end as assists_per90

    from {{ ref('int_fantrax_player_event_totals') }} e
    left join player_event_g_a ga
        on e.player_id = ga.player_id
       and e.event_id  = ga.event_id
    group by 1,2,3
),

-- -------------------------------------------------
-- Fantasy scoring weights for goals/assists by position
-- -------------------------------------------------
score_weights as (

    select
        position,
        max(case when stat_key = 'G'  then points_per_unit end) as pts_per_goal,
        max(case when stat_key = 'AT' then points_per_unit end) as pts_per_assist
    from {{ ref('stg_fantrax_scoring_rules') }}
    where stat_key in ('G','AT')
      and season = '202526'
    group by 1
),

-- -------------------------------------------------
-- Expected goals/assists next fixture (opponent-adjusted + shrunk)
-- -------------------------------------------------
expected_g_a as (

    select
        p.player_id,
        p.scoring_position,
        p.team_short,

        f.opponent,
        f.home_away,

        em.expected_minutes,

        -- base expectation from player rate
        (p.goals_per90   * em.expected_minutes / 90.0) as fantasy_xg_raw,
        (p.assists_per90 * em.expected_minutes / 90.0) as fantasy_xa_raw,

        -- opponent factor: how much opponent concedes vs league average
        -- shrink it to avoid overreaction (0.7 baseline + 0.3 opponent signal)
        (0.7 + 0.3 * (od.opp_ga_per_match / ld.league_avg_ga)) as opp_def_shrink_factor

    from player_rates p
    left join upcoming_fixture f
        on p.player_id = f.player_id
    join expected_minutes em
        on p.player_id = em.player_id
    left join opponent_defense od
        on od.opponent = f.opponent
    cross join league_defense ld
),


-- -------------------------------------------------
-- Final projection
-- -------------------------------------------------
final as (

    select
	p.player_id,
	a.player_name,
        p.scoring_position       as position,
        p.team_short,
        f.opponent,
        f.home_away,

        p.matches_played,
        p.avg_fp,
	p.avg_base_fp,
	p.avg_bonus_fp,

	ega.opp_def_shrink_factor,

        coalesce(p.avg_fp_per_90, p.avg_fp) as avg_fp_per_90,
	p.stdev_base_fp,
        em.expected_minutes,

        coalesce(o.avg_delta_vs_opponent, 0) as opponent_delta_fp,

        -- Base projection
        (p.avg_base_fp_per_90 * em.expected_minutes / 90)
            as projected_fp_base,

        -- Final projection
        /*(p.avg_base_fp_per_90 * em.expected_minutes / 90)
        + coalesce(o.avg_delta_vs_opponent, 0)
            as projected_fp_final,*/
	(p.avg_base_fp_per_90 * em.expected_minutes / 90)
	+ coalesce(o.avg_delta_vs_opponent, 0)
	+ coalesce(cs.expected_cs_points, 0)
	+ ((ega.fantasy_xg_raw * ega.opp_def_shrink_factor) * coalesce(w.pts_per_goal, 0))
	+ ((ega.fantasy_xa_raw * ega.opp_def_shrink_factor) * coalesce(w.pts_per_assist, 0))
	as projected_fp_final,

	-- Clean sheet probability
	case
	    when p.scoring_position = 'D'
	    then cs.expected_cs_points
	    else 0
	end as projected_clean_sheet_points,

	-- xG / xA
	ega.fantasy_xg_raw * ega.opp_def_shrink_factor as fantasy_xg,
	ega.fantasy_xa_raw * ega.opp_def_shrink_factor as fantasy_xa,

	(ega.fantasy_xg_raw * ega.opp_def_shrink_factor) * coalesce(w.pts_per_goal, 0)   as expected_goal_points,
	(ega.fantasy_xa_raw * ega.opp_def_shrink_factor) * coalesce(w.pts_per_assist, 0) as expected_assist_points,

        -- Confidence (sample-size driven)
        (
	    ln(1 + p.matches_played)
	    * (em.expected_minutes / 90.0)
	    * (1 / (1 + coalesce(p.stdev_base_fp, 0)))
	)::numeric(6,3) as confidence_score,

	a.roster_status_label as roster_status,
        a.is_free_agent,
        a.is_waiver_wire,
        a.is_owned

    from player_baseline p
    join expected_minutes em
        on p.player_id = em.player_id
    left join upcoming_fixture f
        on p.player_id = f.player_id
    left join opponent_adjustment o
        on o.scoring_position = p.scoring_position
       and o.opponent = f.opponent
    left join player_availability a
        on p.player_id = a.player_id
    left join expected_clean_sheets cs
	on cs.team_short = p.team_short
	and cs.opponent = f.opponent
	and cs.home_away = f.home_away

    left join expected_g_a ega
	on p.player_id = ega.player_id
    left join score_weights w
	on w.position = p.scoring_position
)

select * from final
