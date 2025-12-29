with base as (

    select
        event_id,
        date::date as match_date,

        stats_json ->> 'Team' as team,

        -- Opponent parsing
        case
            when stats_json ->> 'Opp' like '@%' then replace(stats_json ->> 'Opp', '@', '')
            else stats_json ->> 'Opp'
        end as opponent,

        case
            when stats_json ->> 'Opp' like '@%' then 'A'
            else 'H'
        end as home_away,

        stats_json ->> 'Score' as score_text

    from {{ ref('stg_fantrax_player_scoring') }}
    where event_id is not null

),

parsed as (

    select
        event_id,
        match_date,
        team,
        opponent,
        home_away,

        -- Result letter: W / D / L
        split_part(score_text, ' ', 1) as result,

        -- Goals parsing
        split_part(split_part(score_text, ' ', 2), '-', 1)::int as goals_for,
        split_part(split_part(score_text, ' ', 2), '-', 2)::int as goals_against

    from base
)

select distinct
    event_id,
    match_date,
    team,
    opponent,
    home_away,
    goals_for,
    goals_against,
    result

from parsed
