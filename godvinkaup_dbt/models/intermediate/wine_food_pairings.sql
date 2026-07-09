{{
        config(
            materialized='table'
        )
}}

SELECT
    t1.id as id_wine,
    STRING_AGG(t2.description, ';') AS food_pairings
FROM {{ ref('dim_wines') }} t1
LEFT JOIN {{ source('landing', 'wine_food_translations') }} t2
    ON t1.food_pairing LIKE '%' || t2.id || '%'
    AND t1.food_pairing <> 'N/F'
WHERE LENGTH(t1.food_pairing) > 0
GROUP BY t1.id
