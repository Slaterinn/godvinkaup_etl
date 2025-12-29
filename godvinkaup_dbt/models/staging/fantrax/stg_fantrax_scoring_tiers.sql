select
    position,
    stat_key,
    min_value,
    max_value,
    step_size,
    points_per_step,
    season
from {{ source('landing', 'fantrax_scoring_tiers') }}
