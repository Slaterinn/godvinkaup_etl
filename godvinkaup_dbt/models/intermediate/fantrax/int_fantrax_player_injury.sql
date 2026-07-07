with inj as (

    select
        player_id,

        is_injured,
        injury_status,
        injury_minutes_multiplier,
        injury_text,
        injury_message,
        injury_expected_return_raw,

        analysis_text,
        news_text,
        news_updated_at,

        updated_at as injury_updated_at
    from {{ ref('stg_fantrax_player_news') }}
),

mins as (

    select
        player_id,
        expected_minutes,
        role_label
    from {{ ref('int_fantrax_player_minutes') }}
),

final as (

    select
        i.player_id,

        -- injury core
        coalesce(i.is_injured, false) as is_injured,
        coalesce(i.injury_status, 'healthy') as injury_status,

        -- convenience flags
        case when i.injury_status = 'out' then true else false end as is_out_next_game,
        case when i.injury_status = 'doubtful' then true else false end as is_doubtful_next_game,

        -- raw text for UI/LLM
        i.injury_text,
        i.injury_message,
        i.injury_expected_return_raw,

        -- preserve the staged multiplier (what the string implies)
        coalesce(i.injury_minutes_multiplier, 1.0)::numeric(6,3) as injury_minutes_multiplier,

        -- starter-aware multiplier:
        -- if OUT -> 0
        -- if DOUBTFUL but usually starts -> 1.0 (do not bake uncertainty into projection; let agent explain)
        -- else use staged multiplier
        case
            when i.injury_status = 'out' then 0.0
            when i.injury_status = 'doubtful'
                 and m.role_label = 'starter'
                 and coalesce(m.expected_minutes, 0) >= 70
            then 1.0
            else coalesce(i.injury_minutes_multiplier, 1.0)
        end::numeric(6,3) as injury_minutes_multiplier_effective,

        -- carry news/analysis through
        i.analysis_text,
        i.news_text,
        i.news_updated_at,

        i.injury_updated_at

    from inj i
    left join mins m
      on i.player_id = m.player_id
)

select * from final
