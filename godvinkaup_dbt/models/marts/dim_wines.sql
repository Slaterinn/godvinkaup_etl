{{ config(
    schema='marts',
    materialized='incremental',
    unique_key='id'
) }}

with source as (
    select *
    from {{ ref('stg_all_wines') }}
),

{% if is_incremental() %}

expired as (
    select d.*
    from {{ this }} d
    left join source s on s.id = d.id
    where s.id is null
),

{% endif %}

-- Upserts always run
upserts as (
    select
        s.*,
        1 as valid
    from source s
)

-- Final SELECT
select * from upserts

{% if is_incremental() %}
union all
select
    e.id,
	e.name,
	e.volume,
	e.abv,
	e.price,
	e.country,
	e.origin_place,
	e.origin_district,
	e.grapes,
	e.produced_year,
	e.container_type,
	e.first_on_market,
	e.taste_group,
	e.category,
	e.food_pairing,
	e.producer,
	e.carbon_footprint,
	e.closing,
	e.is_organic,
	e.link,
	e.batch_id,
	e.seller,
    0 as valid
from expired e
{% endif %}
