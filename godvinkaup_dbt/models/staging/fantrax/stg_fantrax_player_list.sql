/*select
    player_id,
    player_name,
    team,
    position,

    next_event_id,
    next_opponent,
    next_home_away,
    next_fixture_text

from {{ source('landing', 'fantrax_player_list') }}
*/

select
    player_id,
    player_name,
    team,
    case when position = 'D,M' then 'D'
	when position = 'M,F' then 'F'
	else position end as position,

    -- -------------------------------------------------
    -- Raw cleaned code (HTML stripped)
    -- -------------------------------------------------
    trim(
        regexp_replace(roster_status_code, '<[^>]+>', '', 'g')
    ) as roster_status_code_raw,

    -- -------------------------------------------------
    -- Canonical roster_status_code
    --   - W for waiver wire
    --   - otherwise keep owner code
    -- -------------------------------------------------
    case
        when roster_status_label ilike 'Waiver Wire%' then 'W'
        else trim(
            regexp_replace(roster_status_code, '<[^>]+>', '', 'g')
        )
    end as roster_status_code,

    -- -------------------------------------------------
    -- Clean roster status label
    -- -------------------------------------------------
    case
        when roster_status_label ilike 'Waiver Wire%' then 'Waiver Wire'
        when roster_status_label ilike 'Free Agent%' then 'Free Agent'
        else roster_status_label
    end as roster_status_label,

    next_event_id,
    next_opponent,
    next_home_away,
    next_fixture_text

from {{ source('landing', 'fantrax_player_list') }}
