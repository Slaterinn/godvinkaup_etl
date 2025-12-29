{{ config(materialized='table') }}

with historical as (

    select
        team                      as team_short,
        opponent,
        home_away,
        goals_for,
        goals_against
    from {{ ref('int_fantrax_event_context') }}

),

-- ---------------------------------------
-- League averages (stability anchor)
-- ---------------------------------------
league_avgs as (

    select
        avg(goals_for::numeric)      as league_avg_goals_for,
        avg(goals_against::numeric)  as league_avg_goals_against
    from historical

),

-- ---------------------------------------
-- Team defensive strength (all opponents)
-- ---------------------------------------
team_defense as (

    select
        team_short,
        avg(goals_against::numeric) as team_ga_per_match,
        count(*)                    as matches_defended
    from historical
    group by team_short

),

-- ---------------------------------------
-- Opponent attacking strength
-- ---------------------------------------
opponent_attack as (

    select
        team_short                  as opponent,
        avg(goals_for::numeric)     as opp_gf_per_match,
        count(*)                    as matches_attacked
    from historical
    group by team_short

),

-- ---------------------------------------
-- Upcoming fixtures (deduplicated)
-- ---------------------------------------
upcoming_fixtures as (

    select distinct
        team                        as team_short,
        next_opponent               as opponent,
        next_home_away              as home_away
    from {{ ref('stg_fantrax_player_list') }}
    where next_opponent is not null

),

-- ---------------------------------------
-- Expected clean sheet probability
-- ---------------------------------------
final as (

    select
        f.team_short,
        f.opponent,
        f.home_away,

        td.team_ga_per_match,
        oa.opp_gf_per_match,

        -- Expected goals conceded (λ)
        (
            (td.team_ga_per_match / la.league_avg_goals_against)
          * (oa.opp_gf_per_match / la.league_avg_goals_for)
          * la.league_avg_goals_for
        )                               as expected_goals_against,

        -- Poisson clean sheet probability
        exp(
            -(
                (td.team_ga_per_match / la.league_avg_goals_against)
              * (oa.opp_gf_per_match / la.league_avg_goals_for)
              * la.league_avg_goals_for
            )
        )                               as clean_sheet_probability,

        -- Fantrax CS points (defenders)
        exp(
            -(
                (td.team_ga_per_match / la.league_avg_goals_against)
              * (oa.opp_gf_per_match / la.league_avg_goals_for)
              * la.league_avg_goals_for
            )
        ) * 6                           as expected_cs_points

    from upcoming_fixtures f
    join team_defense td
        on f.team_short = td.team_short
    join opponent_attack oa
        on f.opponent = oa.opponent
    cross join league_avgs la
)

select * from final
