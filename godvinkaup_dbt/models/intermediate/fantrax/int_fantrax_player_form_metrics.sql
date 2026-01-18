with events as (

    select
        player_id,
        scoring_position,
        team_short,
        event_id,
        event_date,

        fantasy_points,
        base_points,
        event_points,
        minutes_played,
        service_status

    from {{ ref('int_fantrax_player_event_totals') }}

    -- Optional: exclude 0-minute appearances from "form"
    where coalesce(minutes_played, 0) > 0
),

-- Rolling windows computed at the event grain
windows as (

    select
        e.*,

        -- last 5
        avg(fantasy_points) over (
            partition by player_id
            order by event_date, event_id
            rows between 4 preceding and current row
        ) as fp_last_5_avg,

        avg(base_points) over (
            partition by player_id
            order by event_date, event_id
            rows between 4 preceding and current row
        ) as base_fp_last_5_avg,

        avg(event_points) over (
            partition by player_id
            order by event_date, event_id
            rows between 4 preceding and current row
        ) as bonus_fp_last_5_avg,

        stddev_samp(base_points) over (
            partition by player_id
            order by event_date, event_id
            rows between 4 preceding and current row
        ) as stdev_base_fp_last_5,

        sum(minutes_played) over (
            partition by player_id
            order by event_date, event_id
            rows between 4 preceding and current row
        ) as minutes_last_5_sum,

        sum(fantasy_points) over (
            partition by player_id
            order by event_date, event_id
            rows between 4 preceding and current row
        ) as fp_last_5_sum,

        -- last 10
        avg(fantasy_points) over (
            partition by player_id
            order by event_date, event_id
            rows between 9 preceding and current row
        ) as fp_last_10_avg,

        sum(minutes_played) over (
            partition by player_id
            order by event_date, event_id
            rows between 9 preceding and current row
        ) as minutes_last_10_sum,

        sum(fantasy_points) over (
            partition by player_id
            order by event_date, event_id
            rows between 9 preceding and current row
        ) as fp_last_10_sum

    from events e
),

-- Pick the latest snapshot per player (this collapses to one row per player)
latest as (

    select *
    from (
        select
            w.*,
            row_number() over (
                partition by player_id
                order by event_date desc, event_id desc
            ) as rn
        from windows w
    ) x
    where rn = 1
),

-- Season / overall aggregates per player
season as (

    select
        player_id,

        max(scoring_position) as scoring_position,  -- safe if stable; otherwise pick from latest
        max(team_short) as team_short,              -- same comment as above

        count(*) as matches_played,

        avg(fantasy_points) as avg_fp,
        avg(base_points) as avg_base_fp,
        avg(event_points) as avg_bonus_fp,

        stddev_samp(base_points) as stdev_base_fp,

        case
            when nullif(sum(minutes_played), 0) is null then null
            else (sum(fantasy_points) / nullif(sum(minutes_played), 0)) * 90.0
        end as avg_fp_per_90

    from events
    group by player_id
),

final as (

    select
        l.player_id,
	l.scoring_position,
        -- Prefer dimensional attributes from the latest record (less ambiguity)
        l.team_short,


        -- Latest event markers (useful for debugging freshness)
        l.event_id as last_event_id,
        l.event_date as last_event_date,

        -- Season production
        s.matches_played,
        s.avg_fp,
        s.avg_base_fp,
        s.avg_bonus_fp,
        s.stdev_base_fp,
        s.avg_fp_per_90,

        -- Recent form (last 5 vs last 10)
        l.fp_last_5_avg,
        l.fp_last_10_avg,
        (l.fp_last_5_avg - l.fp_last_10_avg) as fp_trend_delta,

        l.base_fp_last_5_avg,
        l.bonus_fp_last_5_avg,

        -- Minutes-weighted per-90 (last 5 / last 10)
        case
            when nullif(l.minutes_last_5_sum, 0) is null then null
            else (l.fp_last_5_sum / nullif(l.minutes_last_5_sum, 0)) * 90.0
        end as fp_last_5_per_90,

        case
            when nullif(l.minutes_last_10_sum, 0) is null then null
            else (l.fp_last_10_sum / nullif(l.minutes_last_10_sum, 0)) * 90.0
        end as fp_last_10_per_90,

        -- Bonus share (interpretability)
        case
            when nullif(l.fp_last_5_avg, 0) is null then null
            else l.bonus_fp_last_5_avg / nullif(l.fp_last_5_avg, 0)
        end as bonus_share_last_5,

        -- Volatility / consistency
        l.stdev_base_fp_last_5,
        (1.0 / (1.0 + coalesce(l.stdev_base_fp_last_5, 0))) as consistency_score,

        -- LLM-friendly labels
        case
            when (l.fp_last_5_avg - l.fp_last_10_avg) >= 2.0 then 'hot'
            when (l.fp_last_5_avg - l.fp_last_10_avg) <= -2.0 then 'cold'
            else 'stable'
        end as form_label,

        case
            when (l.bonus_fp_last_5_avg / nullif(l.fp_last_5_avg, 0)) >= 0.30 then 'bonus-driven'
            when (l.bonus_fp_last_5_avg / nullif(l.fp_last_5_avg, 0)) <= 0.10 then 'base-driven'
            else 'balanced'
        end as scoring_profile_label

    from latest l
    left join season s
        using (player_id)
)

select * from final
