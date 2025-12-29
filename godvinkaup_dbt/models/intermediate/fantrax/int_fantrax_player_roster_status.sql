select
    player_id,
    player_name,
    team,
    position,

    roster_status_code,
    roster_status_label,

    -- -------------------------------------------------
    -- Canonical flags
    -- -------------------------------------------------
    roster_status_code = 'FA' as is_free_agent,
    roster_status_code = 'W'  as is_waiver_wire,
    roster_status_code not in ('FA', 'W') as is_owned,

    -- Owner only if actually owned
    case
        when roster_status_code not in ('FA', 'W')
        then roster_status_code
        else null
    end as owner_code,

    next_opponent,
    next_home_away

from {{ ref('stg_fantrax_player_list') }}
