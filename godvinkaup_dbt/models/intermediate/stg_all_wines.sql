{{
	config(
            materialized='table'
        )
}}

WITH red_wines AS (
    SELECT id
            , name
            , volume
            , abv
            , price
            , country
            , origin_place
            , origin_district
            , grapes
            , produced_year
            , case when container_type = 'FL.' then 'Flaska' end as container_type
            , first_on_market
            , taste_group
            , category
            , food_pairing
            , producer
            , carbon_footprint
            , closing
            , is_organic
            --, special_order
            , link
            , batch_id
            , seller 
	FROM {{ source('landing', 'red_wines') }}
	where container_type in ('FL.', 'PET')
),
white_wines AS (
    SELECT id
            , name
            , volume
            , abv
            , price
            , country
            , origin_place
            , origin_district
            , grapes
            , produced_year
            , case when container_type = 'FL.' then 'Flaska' end as container_type
            , first_on_market
            , taste_group
            , category
            , food_pairing
            , producer
            , carbon_footprint
            , closing
            , is_organic
            --, special_order
            , link
            , batch_id
            , seller 
	FROM {{ source('landing', 'white_wines') }}
	where container_type  in ('FL.', 'PET')
),
sparkling_wines AS (
    SELECT id
            , name
            , volume
            , abv
            , price
            , country
            , origin_place
            , origin_district
            , grapes
            , produced_year
            , case when container_type = 'FL.' then 'Flaska' end as container_type
            , first_on_market
            , taste_group
            , category
            , food_pairing
            , producer
            , carbon_footprint
            , closing
            , is_organic
            --, special_order
            , link
            , batch_id
            , seller 
	FROM {{ source('landing', 'sparkling_wines') }}
	where container_type in ('FL.', 'PET')
),
rose_wines AS (
    SELECT id
            , name
            , volume
            , abv
            , price
            , country
            , origin_place
            , origin_district
            , grapes
            , produced_year
            , case when container_type = 'FL.' then 'Flaska' end as container_type
            , first_on_market
            , taste_group
            , category
            , food_pairing
            , producer
            , carbon_footprint
            , closing
            , is_organic
            --, special_order
            , link
            , batch_id
            , seller
        FROM {{ source('landing', 'rose_wines') }}
        where container_type in ('FL.', 'PET')
),
sante_wines AS (
    SELECT id
            , name
            , size * 10
            , 0
            , price
            , case when country = 'US' then 'Bandaríkin'
                else country end
            , area
            , district
            , case when name like '%Albariño%' then 'Albariño' else grapes end as grapes
            , produced_year
            , 'Flaska'
            , first_sale_date
            , 'N/F'
            , type 
            , 'N/F'
            , producer
            , 0
            , 'N/F'
            , 'true'
            --, 'false'
            , product_url
            , batch_date
            , 'Sante'
        FROM {{ source('landing', 'sante_wines') }}
),
uva_wines AS (
    SELECT wine_id
            , name
            , size
            , 0
            , price
            , case when country = 'Usa' then 'Bandaríkin' else country end as country
            , area
            , origin_district
            , grapes
            , year
            , 'Flaska'
            , CAST(NULL AS DATE)
            , 'N/F'
            , wine_type 
            , 'N/F'
            , producer
            , 0
            , 'N/F'
            , 'true'
            --, 'false'
            , link
            , batch_id
            , 'Uva'
        FROM {{ source('landing', 'uva_wines') }}
)

SELECT * FROM red_wines
UNION ALL
SELECT * FROM white_wines
UNION ALL
SELECT * FROM sparkling_wines
UNION ALL
SELECT * FROM rose_wines
UNION ALL
SELECT * FROM sante_wines
UNION ALL
SELECT * FROM uva_wines
