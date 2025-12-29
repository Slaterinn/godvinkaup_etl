select
    position,
    stat_key,
    stat_name,
    points_per_unit,
    is_positive,
    is_base_stat,
    season
from {{ source('landing', 'fantrax_scoring_rules') }}
