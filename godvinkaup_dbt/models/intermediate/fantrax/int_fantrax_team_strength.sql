
with base as (

    select
        p.event_id,
        p.player_id,
        p.scoring_position,
        p.team_short,
        p.fantasy_points,
        p.minutes_played,
        c.opponent,
        c.home_away

    from {{ ref('int_fantrax_player_event_totals') }} p
    join {{ ref('int_fantrax_event_context') }} c
      on p.event_id = c.event_id
     and p.team_short = c.team

    where
        p.fantasy_points is not null
        and coalesce(p.minutes_played, 90) >= 20
),

-- --------------------------------------------------
-- Player baseline (season average)
-- --------------------------------------------------
player_baseline as (

    select
        player_id,
        avg(fantasy_points) as avg_fp_overall
    from base
    group by player_id
),

-- --------------------------------------------------
-- Delta vs opponent
-- --------------------------------------------------
with_deltas as (

    select
        b.opponent,
        b.scoring_position,
        b.player_id,
        b.fantasy_points,
        pb.avg_fp_overall,
        (b.fantasy_points - pb.avg_fp_overall) as fp_delta
    from base b
    join player_baseline pb
      on b.player_id = pb.player_id
),

-- --------------------------------------------------
-- Aggregate to opponent × position
-- --------------------------------------------------
aggregated as (

    select
        opponent,
        scoring_position,

        count(*) as matches_sampled,

        avg(fantasy_points) as avg_fp_vs_opponent,
        avg(fp_delta) as avg_delta_vs_opponent

    from with_deltas
    group by opponent, scoring_position
)

select *
from aggregated
where matches_sampled >= 10
