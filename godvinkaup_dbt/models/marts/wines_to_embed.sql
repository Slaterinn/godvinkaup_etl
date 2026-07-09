{{ config(
    schema = 'marts'
) }}

-- models/marts/wines_to_embed.sql


select
  pk_wine
, wine_name
, volume
, price
, country
, origin_place
, origin_district
, grapes
, produced_year
, category
, producer
, seller
, link as seller_link
, link_vivino
, recommendation
, image_url_use
, rating
, rating_count
,
case when category = 'Red Wine' then 'Þetta er rauðvín.' when category = 'White Wine' then 'Þetta er hvítvín.' when category = 'Sparkling Wine' then 'Þetta er freyðivín.' when category = 'Rose' then 'Þetta er rósavín.' else '' end ||
case when sweetness != 'N/F' then sweetness || '.' else '' end  ||
case when boldness != 'N/F' then boldness || '.' else '' end ||
case when country != 'Óskráð' then ' Uppruni víns er ' || country || ', ' else '' end ||
case
  when origin_place != '' and origin_district != 'Óskráð'
    then origin_place || ', ' || origin_district || '. '
  when origin_place != '' then origin_place || '. '
  when origin_district != 'Óskráð' then origin_district || '. '
  else ''
end ||
case when grapes != '' then 'Þrúgur vínsins eru ' || grapes || '.' else '' end ||
' Vínframleiðandinn heitir ' || coalesce(producer, 'óþekktur framleiðandi') || '. ' ||
case when produced_year is not null and produced_year != 0 then 'Árgangur: ' || produced_year || '. ' else '' end ||
case when food_pairings not in ('', 'N/F') then 'Matarpörun: ' || REPLACE(food_pairings, ';', ',') || '.' else '' end ||
case when description not in ('N/A', 'N/F') then ' ' || TRIM(BOTH '.' FROM description) || '.' else '' end ||
' Hægt er að kaupa vínið hjá ' || seller || '.' ||
case when recommendation >= 0.95 then ' Talið framúrskarandi kaup miðað við gæði og verð. '
	 when recommendation >= 0.85 then ' Talið frábær kaup miðað við gæði og verð. '
	 when recommendation >= 0.75 then ' Talið mjög góð kaup miðað við gæði og verð. '
	 when recommendation >= 0.65 then ' Talið góð kaup miðað við gæði og verð. '
	 when rating >= 4.2 		  then ' Notendur vivino gefa þessu víni mjög háa einkunn.'
	 else '' end ||
'Einkunn á vivino: ' || rating || ' sem telst sem ' ||
case when rating >= 4.2 then 'framúrskarandi'
	 when rating >= 4 then 'mjög góð'
	 when rating >=3.8 then 'góð'
	 when rating >= 3.6 then 'ágæt'
	 else 'slæm' end || ' einkunn'
' Verð: ' || price::numeric::integer || ' kr.'
as text_to_embed
from {{ ref('wines') }}
