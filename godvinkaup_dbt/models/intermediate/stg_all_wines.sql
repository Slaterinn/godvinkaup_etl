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
            , CASE
                    WHEN container_type = 'PET' THEN 'Plast'
                    WHEN container_type = 'STK.' THEN 'Stykki'
                    WHEN container_type = 'DS.' THEN 'Dós'
                    WHEN container_type = 'FL.' THEN 'Flaska'
                    ELSE container_type
                END AS container_type
            , first_on_market
            , CASE
                    WHEN taste_group = '01TM' THEN 'Kröftugt og millisætt'
                    WHEN taste_group = '01MM' THEN 'Meðalfyllt og millisætt'
                    WHEN taste_group = '01TS' THEN 'Kröftugt og sætt'
                    WHEN taste_group = '01MS' THEN 'Meðalfyllt og sætt'
                    WHEN taste_group = '01LM' THEN 'Létt og millisætt'
                    WHEN taste_group = '01X' THEN 'Eftirréttarvín - sætvín'
                    WHEN taste_group = '01LS' THEN 'Létt og sætt'
                    WHEN taste_group = '01L' THEN 'Létt og ósætt'
                    WHEN taste_group = '01M' THEN 'Meðalfyllt og ósætt'
                    WHEN taste_group = '01T' THEN 'Kröftugt og ósætt'
                    WHEN taste_group = '02TM' THEN 'Kröftugt og millisætt'
                    WHEN taste_group = '02LS' THEN 'Létt og sætt'
                    WHEN taste_group = '02T' THEN 'Kröftugt og ósætt'
                    WHEN taste_group = '02LM' THEN 'Létt og millisætt'
                    WHEN taste_group = '02MS' THEN 'Meðalfyllt og sætt'
                    WHEN taste_group = '02TS' THEN 'Kröftugt og sætt'
                    WHEN taste_group = '02X' THEN 'Eftirréttarvín - sætvín'
                    WHEN taste_group = '02L' THEN 'Létt og ósætt'
                    WHEN taste_group = '02M' THEN 'Meðalfyllt og ósætt'
                    WHEN taste_group = '02MM' THEN 'Kröftugt og ósætt'
                    WHEN taste_group = '03M' THEN 'Millisætt'
                    WHEN taste_group = '03S' THEN 'Sætt'
                    WHEN taste_group = '03' THEN 'Ósætt'
                    WHEN taste_group = '04' THEN 'Ósætt'
                    WHEN taste_group = '04M' THEN 'Millisætt'
                    WHEN taste_group = '04S' THEN 'Sætt'
                END AS taste_group
            , category
            , food_pairing
            , producer
            , carbon_footprint
            , closing
            , is_organic
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
            , CASE
                    WHEN container_type = 'PET' THEN 'Plast'
                    WHEN container_type = 'STK.' THEN 'Stykki'
                    WHEN container_type = 'DS.' THEN 'Dós'
                    WHEN container_type = 'FL.' THEN 'Flaska'
                    ELSE container_type
                END AS container_type
            , first_on_market
            , CASE
                    WHEN taste_group = '01TM' THEN 'Kröftugt og millisætt'
                    WHEN taste_group = '01MM' THEN 'Meðalfyllt og millisætt'
                    WHEN taste_group = '01TS' THEN 'Kröftugt og sætt'
                    WHEN taste_group = '01MS' THEN 'Meðalfyllt og sætt'
                    WHEN taste_group = '01LM' THEN 'Létt og millisætt'
                    WHEN taste_group = '01X' THEN 'Eftirréttarvín - sætvín'
                    WHEN taste_group = '01LS' THEN 'Létt og sætt'
                    WHEN taste_group = '01L' THEN 'Létt og ósætt'
                    WHEN taste_group = '01M' THEN 'Meðalfyllt og ósætt'
                    WHEN taste_group = '01T' THEN 'Kröftugt og ósætt'
                    WHEN taste_group = '02TM' THEN 'Kröftugt og millisætt'
                    WHEN taste_group = '02LS' THEN 'Létt og sætt'
                    WHEN taste_group = '02T' THEN 'Kröftugt og ósætt'
                    WHEN taste_group = '02LM' THEN 'Létt og millisætt'
                    WHEN taste_group = '02MS' THEN 'Meðalfyllt og sætt'
                    WHEN taste_group = '02TS' THEN 'Kröftugt og sætt'
                    WHEN taste_group = '02X' THEN 'Eftirréttarvín - sætvín'
                    WHEN taste_group = '02L' THEN 'Létt og ósætt'
                    WHEN taste_group = '02M' THEN 'Meðalfyllt og ósætt'
                    WHEN taste_group = '02MM' THEN 'Kröftugt og ósætt'
                    WHEN taste_group = '03M' THEN 'Millisætt'
                    WHEN taste_group = '03S' THEN 'Sætt'
                    WHEN taste_group = '03' THEN 'Ósætt'
                    WHEN taste_group = '04' THEN 'Ósætt'
                    WHEN taste_group = '04M' THEN 'Millisætt'
                    WHEN taste_group = '04S' THEN 'Sætt'
                END AS taste_group
            , category
            , food_pairing
            , producer
            , carbon_footprint
            , closing
            , is_organic
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
            , CASE
                    WHEN container_type = 'PET' THEN 'Plast'
                    WHEN container_type = 'STK.' THEN 'Stykki'
                    WHEN container_type = 'DS.' THEN 'Dós'
                    WHEN container_type = 'FL.' THEN 'Flaska'
                    ELSE container_type
                END AS container_type
            , first_on_market
            , CASE
                    WHEN taste_group = '01TM' THEN 'Kröftugt og millisætt'
                    WHEN taste_group = '01MM' THEN 'Meðalfyllt og millisætt'
                    WHEN taste_group = '01TS' THEN 'Kröftugt og sætt'
                    WHEN taste_group = '01MS' THEN 'Meðalfyllt og sætt'
                    WHEN taste_group = '01LM' THEN 'Létt og millisætt'
                    WHEN taste_group = '01X' THEN 'Eftirréttarvín - sætvín'
                    WHEN taste_group = '01LS' THEN 'Létt og sætt'
                    WHEN taste_group = '01L' THEN 'Létt og ósætt'
                    WHEN taste_group = '01M' THEN 'Meðalfyllt og ósætt'
                    WHEN taste_group = '01T' THEN 'Kröftugt og ósætt'
                    WHEN taste_group = '02TM' THEN 'Kröftugt og millisætt'
                    WHEN taste_group = '02LS' THEN 'Létt og sætt'
                    WHEN taste_group = '02T' THEN 'Kröftugt og ósætt'
                    WHEN taste_group = '02LM' THEN 'Létt og millisætt'
                    WHEN taste_group = '02MS' THEN 'Meðalfyllt og sætt'
                    WHEN taste_group = '02TS' THEN 'Kröftugt og sætt'
                    WHEN taste_group = '02X' THEN 'Eftirréttarvín - sætvín'
                    WHEN taste_group = '02L' THEN 'Létt og ósætt'
                    WHEN taste_group = '02M' THEN 'Meðalfyllt og ósætt'
                    WHEN taste_group = '02MM' THEN 'Kröftugt og ósætt'
                    WHEN taste_group = '03M' THEN 'Millisætt'
                    WHEN taste_group = '03S' THEN 'Sætt'
                    WHEN taste_group = '03' THEN 'Ósætt'
                    WHEN taste_group = '04' THEN 'Ósætt'
                    WHEN taste_group = '04M' THEN 'Millisætt'
                    WHEN taste_group = '04S' THEN 'Sætt'
                END AS taste_group
            , category
            , food_pairing
            , producer
            , carbon_footprint
            , closing
            , is_organic
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
            , CASE
                    WHEN container_type = 'PET' THEN 'Plast'
                    WHEN container_type = 'STK.' THEN 'Stykki'
                    WHEN container_type = 'DS.' THEN 'Dós'
                    WHEN container_type = 'FL.' THEN 'Flaska'
                    ELSE container_type
                END AS container_type
            , first_on_market
            , CASE
                    WHEN taste_group = '01TM' THEN 'Kröftugt og millisætt'
                    WHEN taste_group = '01MM' THEN 'Meðalfyllt og millisætt'
                    WHEN taste_group = '01TS' THEN 'Kröftugt og sætt'
                    WHEN taste_group = '01MS' THEN 'Meðalfyllt og sætt'
                    WHEN taste_group = '01LM' THEN 'Létt og millisætt'
                    WHEN taste_group = '01X' THEN 'Eftirréttarvín - sætvín'
                    WHEN taste_group = '01LS' THEN 'Létt og sætt'
                    WHEN taste_group = '01L' THEN 'Létt og ósætt'
                    WHEN taste_group = '01M' THEN 'Meðalfyllt og ósætt'
                    WHEN taste_group = '01T' THEN 'Kröftugt og ósætt'
                    WHEN taste_group = '02TM' THEN 'Kröftugt og millisætt'
                    WHEN taste_group = '02LS' THEN 'Létt og sætt'
                    WHEN taste_group = '02T' THEN 'Kröftugt og ósætt'
                    WHEN taste_group = '02LM' THEN 'Létt og millisætt'
                    WHEN taste_group = '02MS' THEN 'Meðalfyllt og sætt'
                    WHEN taste_group = '02TS' THEN 'Kröftugt og sætt'
                    WHEN taste_group = '02X' THEN 'Eftirréttarvín - sætvín'
                    WHEN taste_group = '02L' THEN 'Létt og ósætt'
                    WHEN taste_group = '02M' THEN 'Meðalfyllt og ósætt'
                    WHEN taste_group = '02MM' THEN 'Kröftugt og ósætt'
                    WHEN taste_group = '03M' THEN 'Millisætt'
                    WHEN taste_group = '03S' THEN 'Sætt'
                    WHEN taste_group = '03' THEN 'Ósætt'
                    WHEN taste_group = '04' THEN 'Ósætt'
                    WHEN taste_group = '04M' THEN 'Millisætt'
                    WHEN taste_group = '04S' THEN 'Sætt'
                END AS taste_group
            , category
            , food_pairing
            , producer
            , carbon_footprint
            , closing
            , is_organic
            , link
            , batch_id
            , seller
        FROM {{ source('landing', 'rose_wines') }}
        where container_type in ('FL.', 'PET')
),
sante_wines AS (
    SELECT id
            , name
            , size
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
            , CASE 
                    WHEN type IN ('Freyðivín', 'Kampavín') THEN 'Sparkling Wine'
                    WHEN type = 'Rauðvín' THEN 'Red Wine'
                    WHEN type = 'Rósavín' THEN 'Rose'
                    WHEN type = 'Hvítvín' THEN 'White Wine'
                    ELSE type
                END AS category 
            , 'N/F'
            , producer
            , 0
            , 'N/F'
            , 'true'
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
            , case when country = 'USA' then 'bandaríkin' 
		when country = 'Suður Afríka' then 'suðurafríka' 
		when country = 'Nýja Sjáland' then 'nýjasjáland' else country end as country
            , area
            , origin_district
            , grapes
            , year
            , 'Flaska'
            , CAST(NULL AS DATE)
            , 'N/F'
            , CASE 
                            WHEN wine_type = 'Rauðvín' THEN 'Red Wine'
                            WHEN wine_type = 'Hvítvín' THEN 'White Wine'
                            WHEN wine_type = 'Rósavín' THEN 'Rose'
                            WHEN wine_type IN ('Cava', 'Freyðivín', 'Kampavín') THEN 'Sparkling Wine'
                            ELSE wine_type
                        END AS category
            , 'N/F'
            , producer
            , 0
            , 'N/F'
            , 'true'
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
