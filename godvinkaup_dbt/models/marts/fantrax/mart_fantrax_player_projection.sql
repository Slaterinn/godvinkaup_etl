with player_baseline as (

    select
        pe.player_id,
        pe.scoring_position,
        pe.team_short,
        tn.team_name                        as team_full_name,

        pe.matches_played                   as matches_played,
        pe.avg_fp                           as avg_fp,
        pe.avg_base_fp                      as avg_base_fp,
        pe.avg_bonus_fp                     as avg_bonus_fp,

        pe.stdev_base_fp                    as stdev_base_fp,

        pe.avg_fp_per_90                    as avg_fp_per_90,
        pe.avg_base_fp_per_90               as avg_base_fp_per_90,

        pe.fp_last_5_avg                    as avg_fp_last_5,
        pe.fp_last_10_avg                   as avg_fp_last_10,
        pe.fp_last_5_per_90                 as avg_fp_last_5_per_90,
        pe.consistency_score                as consistency_score,
        pe.form_label                       as form_label,
        pe.scoring_profile_label            as scoring_profile_label

    from {{ ref('int_fantrax_player_form_metrics') }} pe
    join {{ ref('stg_fantrax_team_names') }} tn
      on pe.team_short = tn.team_short
),

-- -------------------------------------------------
-- Expected minutes (simple & explainable)
-- -------------------------------------------------
player_minutes as (

    select
        pm.player_id,
        pm.avg_minutes_last_5,
        pm.avg_minutes_before,
        pm.expected_minutes,
        pm.role_label,
        pm.minutes_trend
    from {{ ref('int_fantrax_player_minutes') }} pm
),

-- -------------------------------------------------
-- Injury / News context (player-grain)
-- -------------------------------------------------
player_injury as (

    select
        player_id,
        coalesce(is_injured, false) as is_injured,
        injury_status,
        injury_text,
        analysis_text,
        news_text,
        -- If your intermediate provides these, great; otherwise fallback logic below handles it.
        is_out_next_game,
        injury_minutes_multiplier
    from {{ ref('int_fantrax_player_injury') }}
),

-- -------------------------------------------------
-- Upcoming fixture context
-- -------------------------------------------------
upcoming_fixture as (

    select
        pl.player_id,
        pl.next_opponent                 as opponent,
        tn.team_name                     as opponent_name,
        pl.next_home_away                as home_away
    from {{ ref('stg_fantrax_player_list') }} pl
    join {{ ref('stg_fantrax_team_names') }} tn
      on pl.next_opponent = tn.team_short
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
-- NOTE: use expected_minutes_adj (injury-aware) rather than pm.expected_minutes
-- -------------------------------------------------
expected_g_a as (

    select
        p.player_id,
        p.scoring_position,
        p.team_short,

        f.opponent,
        f.home_away,

        proj.expected_minutes_adj,

        (p.goals_per90   * proj.expected_minutes_adj / 90.0) as fantasy_xg_raw,
        (p.assists_per90 * proj.expected_minutes_adj / 90.0) as fantasy_xa_raw,

        (0.7 + 0.3 * (od.opp_ga_per_match / ld.league_avg_ga)) as opp_def_shrink_factor

    from player_rates p
    left join upcoming_fixture f
      on p.player_id = f.player_id
    join (
        -- build a minimal injury-aware minutes projection table for reuse
        select
            pm.player_id,

            pm.expected_minutes,
            pm.role_label,

            -- OUT = 0 minutes
            case
                when coalesce(inj.is_out_next_game, false)
                     or (inj.injury_status = 'out')
                     or (inj.injury_text ilike '%out for next game%')
                then 0.0

                -- DOUBTFUL: if usually starts, keep minutes; else dampen
                when (inj.injury_status = 'doubtful'
                      or inj.injury_text ilike '%game-time decision%'
                      or inj.injury_text ilike '%late fitness test%')
                     and not (pm.role_label = 'starter' and pm.expected_minutes >= 70)
                then pm.expected_minutes * coalesce(inj.injury_minutes_multiplier, 0.60)

                -- injured but unknown: mild dampener
                when coalesce(inj.is_injured, false)
                then pm.expected_minutes * coalesce(inj.injury_minutes_multiplier, 0.85)

                else pm.expected_minutes
            end as expected_minutes_adj

        from player_minutes pm
        left join player_injury inj
          on pm.player_id = inj.player_id
    ) proj
      on p.player_id = proj.player_id

    left join opponent_defense od
      on od.opponent = f.opponent
    cross join league_defense ld
),

-- -------------------------------------------------
-- Projection base (injury-aware minutes + carry injury fields)
-- -------------------------------------------------
projection_base as (

    select
        p.player_id,
        a.player_name,
        p.scoring_position       as position,
        p.team_short,
        p.team_full_name,
        f.opponent,
        f.opponent_name as opponent_full_name,
        f.home_away,

        p.matches_played,
        p.avg_fp,
        p.avg_base_fp,
        p.avg_bonus_fp,

        p.avg_fp_last_5,
        p.avg_fp_last_10,
        p.consistency_score,
        p.form_label,
        p.scoring_profile_label,

        ega.opp_def_shrink_factor,

        coalesce(p.avg_fp_per_90, p.avg_fp) as avg_fp_per_90,
        p.stdev_base_fp,

        pm.expected_minutes,
        pm.avg_minutes_last_5,
        pm.avg_minutes_before,
        pm.role_label,
        pm.minutes_trend,

        -- Injury fields (for UI + LLM)
        coalesce(inj.is_injured, false) as is_injured,
        inj.injury_status,
        inj.injury_text,
        inj.analysis_text,
        inj.news_text,

        -- Injury-aware minutes (same logic as used in expected_g_a)
        case
            when coalesce(inj.is_out_next_game, false)
                 or (inj.injury_status = 'out')
                 or (inj.injury_text ilike '%out for next game%')
            then 0.0

            when (inj.injury_status = 'doubtful'
                  or inj.injury_text ilike '%game-time decision%'
                  or inj.injury_text ilike '%late fitness test%')
                 and not (pm.role_label = 'starter' and pm.expected_minutes >= 70)
            then pm.expected_minutes * coalesce(inj.injury_minutes_multiplier, 0.60)

            when coalesce(inj.is_injured, false)
            then pm.expected_minutes * coalesce(inj.injury_minutes_multiplier, 0.85)

            else pm.expected_minutes
        end as expected_minutes_adj,

        coalesce(o.avg_delta_vs_opponent, 0) as opponent_delta_fp,

        greatest(
            0.0,
            least(
                0.35,
                (ln(1 + p.matches_played) / 5.0) * coalesce(p.consistency_score, 0.5)
            )
        ) as form_weight,

        p.avg_base_fp_per_90,
        p.avg_fp_last_5_per_90,

	-- Final projection (injury-aware)
  	case
	    when expected_minutes_adj = 0 then 0
 	    else
                (p.avg_base_fp_per_90 * expected_minutes_adj / 90.0)
                + coalesce(o.avg_delta_vs_opponent, 0)
                + coalesce(cs.expected_cs_points, 0)
                + ((ega.fantasy_xg_raw * ega.opp_def_shrink_factor) * coalesce(w.pts_per_goal, 0))
                + ((ega.fantasy_xa_raw * ega.opp_def_shrink_factor) * coalesce(w.pts_per_assist, 0))
	end as projected_fp_final_raw,

	case
            when p.scoring_position = 'D'
            then cs.expected_cs_points
            else 0
        end as projected_clean_sheet_points,

        ega.fantasy_xg_raw * ega.opp_def_shrink_factor as fantasy_xg,
        ega.fantasy_xa_raw * ega.opp_def_shrink_factor as fantasy_xa,

        (ega.fantasy_xg_raw * ega.opp_def_shrink_factor) * coalesce(w.pts_per_goal, 0)   as expected_goal_points,
        (ega.fantasy_xa_raw * ega.opp_def_shrink_factor) * coalesce(w.pts_per_assist, 0) as expected_assist_points,

	(
  	    ln(1 + p.matches_played)
	    * (expected_minutes_adj / 90.0)
	    * (1 / (1 + coalesce(p.stdev_base_fp, 0)))
	)::numeric(6,3) as confidence_score,

        a.roster_status_label as roster_status,
        a.is_free_agent,
        a.is_waiver_wire,
        a.is_owned

    from player_baseline p
    join player_minutes pm
      on p.player_id = pm.player_id
    left join player_injury inj
      on p.player_id = inj.player_id
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
),

final as (
    select
        *,

        (
            (1 - form_weight) * avg_base_fp_per_90
          + form_weight * coalesce(avg_fp_last_5_per_90, avg_base_fp_per_90)
        ) as blended_base_fp_per_90,

        (
            (
                (1 - form_weight) * avg_base_fp_per_90
              + form_weight * coalesce(avg_fp_last_5_per_90, avg_base_fp_per_90)
            ) * expected_minutes_adj / 90.0
        ) as projected_fp_base,

        -- If OUT, enforce projected_fp_final = 0
        case
            when expected_minutes_adj = 0 then 0
            else projected_fp_final_raw
        end as projected_fp_final

    from projection_base
)

select
    -- keep original name projected_fp_final for downstream compatibility
    -- overwrite with injury-aware final
    final.*
from final
