{{ config(
    schema = 'marts'
) }}

-- models/marts/wines.sql

select
      vinbud.id as pk_wine
    , vino.vivino_id
    , vinbud.name as wine_name
    , vino.wine_name as wine_name_vivino
    , vinbud.volume
    , vinbud.abv
    , vinbud.price
    , case 
        when vinbud.country in ('', 'N/F') then 'Óskráð'
        else upper(left(vinbud.country, 1)) || lower(substring(vinbud.country from 2)) 
      end as country
    , vinbud.origin_place
    , case 
        when vinbud.origin_district in ('', 'ENGINN', 'N/F', '-') then 'Óskráð'
        else vinbud.origin_district 
      end as origin_district
    , case 
        when vinbud.name like '%Albariño%' then 'Albariño'
        else vinbud.grapes 
      end as grapes 
    , vinbud.produced_year
    , vinbud.container_type
    , vinbud.first_on_market
    , vinbud.taste_group
    , vinbud.category
    , vinbud.food_pairing
    , vinbud.producer
    , vinbud.seller
    , vino.producer as producer_vivino
    , vinbud.carbon_footprint
    , vinbud.closing
    , vinbud.is_organic
    , vinbud.link
    , vino.wine_url as link_vivino
    --, vinbud.insert_date
    , vino.rating
    , vino.rating_count
    , vino.image_url
    , case 
        when image_url like '%pl_375x500%' 
        then replace(image_url, 'pl_375x500', 'pb_300x300') 
        else image_url 
      end as image_url_use
    , power(vino.rating, 3.8) as rating_adjusted
    , case 
        when vino.rating_count < 100 then 0.8
        when vino.rating_count >= 100 and vino.rating_count < 500 then 0.9
        when vino.rating_count >= 500 and vino.rating_count < 1000 then 0.95
        else 1 
      end as rating_count_index
    , case 
        when vinbud.is_organic = 'true' then 1.1 
        else 1 
      end as rating_organic_index
    , round(
        case 
          when (vinbud.volume / power(vinbud.price, 0.5)) * power(vino.rating, 3.8) * 
               (case 
                    when vino.rating_count < 100 then 0.8
                    when vino.rating_count >= 100 and vino.rating_count < 500 then 0.9
                    when vino.rating_count >= 500 and vino.rating_count < 1000 then 0.95
                    else 1 
                end) / 2150 >= 1.6 
          then 1
          else (vinbud.volume / power(vinbud.price, 0.5)) * power(vino.rating, 3.8) * 
               (case 
                    when vino.rating_count < 100 then 0.8
                    when vino.rating_count >= 100 and vino.rating_count < 500 then 0.9
                    when vino.rating_count >= 500 and vino.rating_count < 1000 then 0.95
                    else 1 
                end) / 2150 / 1.6 
        end * 
        case 
          when vinbud.is_organic = 'true' then 1.1 
          else 1 
        end
    , 2) as recommendation
    , vino.insert_date as insert_date_vivino
    , vino.modified_date as modified_date_vivino
    , case 
        when vinbud.taste_group in ('Ósætt', 'Meðalfyllt og ósætt', 'Létt og ósætt', 'Kröftugt og ósætt') then 'Ósætt'
        when vinbud.taste_group in ('Millisætt', 'Meðalfyllt og millisætt', 'Létt og millisætt', 'Kröftugt og millisætt') then 'Millisætt'
        when vinbud.taste_group in ('Sætt', 'Meðalfyllt og sætt', 'Létt og sætt', 'Kröftugt og sætt') then 'Sætt'
        when vinbud.taste_group = 'Eftirréttarvín - sætvín' then 'Eftirréttarvín'
        else 'N/F' 
      end as sweetness
    , case 
        when vinbud.taste_group in ('Kröftugt og millisætt', 'Kröftugt og sætt', 'Kröftugt og ósætt') then 'Kröftugt'
        when vinbud.taste_group in ('Meðalfyllt og millisætt', 'Meðalfyllt og sætt', 'Meðalfyllt og ósætt') then 'Meðalfyllt'
        when vinbud.taste_group in ('Létt og millisætt', 'Létt og ósætt', 'Létt og sætt') then 'Létt'
        when vinbud.taste_group = 'Eftirréttarvín - sætvín' then 'Eftirréttarvín'
        else 'N/F' 
      end as boldness
    , FP.food_pairings
from {{ ref('dim_wines') }} vinbud
inner join {{ source('marts', 'wine_ratings_vivino') }} vino 
    on vinbud.id = vino.pk_wine
left join {{ ref('wine_food_pairings') }} FP 
    on FP.id_wine = vinbud.id
where vinbud.volume = 750
  and vinbud.price > 0
  and vinbud.valid = '1'
