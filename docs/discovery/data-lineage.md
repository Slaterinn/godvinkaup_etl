# End-to-End Data Lineage (Verified)

Lineage is traced from imports, `source()`/`ref()` calls, SQL joins, and file read/writes actually
present in the repository — not inferred from filenames alone.

## Lineage table 1 — ÁTVR / Vínbúðin (red, white, rosé, sparkling)

| Hop | File / object | Detail |
|---|---|---|
| 1. Source | `https://www.vinbudin.is/addons/origo/module/ajaxwebservices/search.asmx/DoSearch` | AJAX endpoint, `category=red\|white\|rose\|bubbly`, `count=2000`, `orderBy=random` |
| 2. Scraper | `dags/scripts/scrape_{red,white,rose,sparkling}_wines.py` `fetch_and_insert_*` | One nearly-identical function per category (see technical-debt-register: duplicated logic) |
| 3. Parsing/normalization | same file, inline `dict(...)` construction | Maps `ProductID→id`, `ProductName→name`, `ProductBottledVolume→volume`, etc.; `category` is hardcoded per file ("Red Wine"/"White Wine"/"Rose"/"Sparkling Wine"); `seller` hardcoded `"ÁTVR"` |
| 4. DB write | same file, `psycopg2.extras.execute_batch` via `PostgresHook(postgres_conn_id="postgres_godvinkaup")` | `DROP TABLE ... CASCADE; CREATE UNLOGGED TABLE landing.{red,white,rose,sparkling}_wines` every run — full replace, no history |
| 5. Raw/link enrichment | `dags/scripts/fix_atvr_links.py` | Backfills missing links by probing `vinbudin.is` product-ID URL variants; writes `landing.atvr_wine_links` |
| 5b. Description enrichment | `dags/scripts/scrape_atvr_descriptions.py` | Scrapes each wine's ÁTVR product page for a description span; writes `landing.atvr_wine_descriptions` (upsert on `wine_id`) |
| 6. dbt source | `godvinkaup_dbt/models/staging/src_landing.yml:6-9,13-14` | `source('landing','red_wines')` etc., `atvr_wine_links`, `atvr_wine_descriptions` |
| 7. Intermediate | `godvinkaup_dbt/models/intermediate/stg_all_wines.sql:7-68` (red), `:69-130` (white), `:132-193` (sparkling), `:195-256` (rosé) | Each CTE left-joins descriptions/links, translates `container_type`/`taste_group` codes to Icelandic labels, filters `container_type in ('FL.','PET')` |
| 8. Union | `stg_all_wines.sql:327-337` | `UNION ALL` of all 6 category CTEs (incl. Sante, Uva below) |
| 9. Marts (dim) | `godvinkaup_dbt/models/marts/dim_wines.sql` | Incremental over `ref('stg_all_wines')`, `unique_key='id'`, adds `valid` flag (1 = current, 0 = expired) |
| 10. Marts (wines) | `godvinkaup_dbt/models/marts/wines.sql` | Inner-joins `dim_wines` to Vivino ratings (see vivino-dependency-map.md), computes `recommendation`, filters `volume in (0,750)`, `price > 0`, `valid = '1'` |
| 11. Marts (embed) | `godvinkaup_dbt/models/marts/wines_to_embed.sql` | Builds `text_to_embed` |
| 12. Export | `dags/scripts/export_wines_to_json.py:14` | `SELECT * FROM marts.wines WHERE rating > 3.4` → `wines_json.json` |
| 13. Website | `dags/scripts/push_gv_to_github.py` | Pushes `wines_json.json` to `Slaterinn/godvinkaup` (external repo, branch `master`, path `data/wines_json.json`) |
| 13b. Embedding | `dags/scripts/embed_wines.py` | `SELECT ... FROM marts.wines_to_embed WHERE recommendation >= 0.5` → OpenAI embeddings → Qdrant `wines_embeddings` |

## Lineage table 2 — Sante (sante.is)

| Hop | File / object | Detail |
|---|---|---|
| 1. Source | `https://sante.is/collections/lettvin` (filters) and `.../products.json?limit=1000` (products) | Shopify storefront |
| 2. Scraper | `dags/scripts/scrape_sante_filters.py` (filter taxonomy), `dags/scripts/scrape_sante_wines.py` (products) | Raw `psycopg2.connect(host="192.168.86.226", ..., password="postgres")` — hardcoded, bypasses Airflow connection |
| 3. Parsing/normalization | `scrape_sante_wines.py:129-231` | Extracts vintage from title/tags, size from title/tags, country/area/grapes matched against the scraped filter taxonomy via `normalize_str` (NFKD ASCII fold), a hardcoded `wine_country_map` region→country fallback, HTML-stripped description |
| 4. DB write | `scrape_sante_filters.py` → `landing.sante_wine_filters` (drop/recreate); `scrape_sante_wines.py` → `landing.sante_wines` (drop/recreate) | |
| 6. dbt source | `src_landing.yml:10` | `source('landing','sante_wines')` |
| 7. Intermediate | `stg_all_wines.sql:258-291` `sante_wines` CTE | Re-maps type codes (`Rauðvín→Red Wine`, etc.), filters `available = 'true'`, forces bottle size default 750ml |
| 8-13 | Same as ÁTVR from step 8 onward | Sante rows flow through the same `UNION ALL` → `dim_wines` → `wines` → export/embed path |

## Lineage table 3 — Uva Vino (uvavino.is)

| Hop | File / object | Detail |
|---|---|---|
| 1. Source | `https://uvavino.is/wp-json/wc/store/products` | WooCommerce Store API, paginated |
| 2. Scraper | `dags/scripts/scrape_uva_wines.py:14-32 fetch_all_products` | Uses `PostgresHook(postgres_conn_id="postgres_godvinkaup")` (correct pattern, unlike Sante/Vivino) |
| 3. Parsing/normalization | `scrape_uva_wines.py:35-90` | `wine_id = "UVA" + product id` (namespaced, unlike ÁTVR/Sante raw numeric IDs); extracts type/area/country/grapes/food-pairings from WooCommerce attributes and tags by numeric attribute/term ID (magic numbers `[15]`, `[13,116]`, `[9]`, `[7]`, category IDs `572/598` to skip, etc. — undocumented mapping) |
| 4. DB write | `scrape_uva_wines.py:101-121` | `landing.uva_wines` (drop/recreate) |
| 6. dbt source | `src_landing.yml:11` | `source('landing','uva_wines')` |
| 7. Intermediate | `stg_all_wines.sql:292-324` `uva_wines` CTE | Re-maps country spellings (`Suður Afríka→suðurafríka` etc.), wine-type codes, replaces `,`→`;` in food pairings |
| 8-13 | Same as ÁTVR from step 8 onward | |

## Lineage table 4 — Vivino (vivino.com)

| Hop | File / object | Detail |
|---|---|---|
| 1. Source | `https://www.vivino.com/search/wines?q=<name>` | Public search page, JSON-LD block scraped |
| 2. Scraper | `dags/scripts/scrape_vivino_ratings.py:85-110 fetch_vivino_results` | 3 retry attempts, random UA/referer headers, hardcoded `psycopg2.connect(host="192.168.86.226", ..., password="Slater168")` — a *different* hardcoded password from Sante's |
| 3. Matching | `scrape_vivino_ratings.py:112-152 score_match / select_best_match` | Fuzzy `SequenceMatcher` name+producer scoring against up to 6 candidates |
| 4. DB write | `scrape_vivino_ratings.py:61-78 insert_bridge_wine` | `marts.wine_ratings_vivino` upsert on `pk_wine` — note this table lives in the `marts` schema, not `landing`, and its DDL is not tracked in this repo |
| 5. Selection of wines to look up | `scrape_vivino_ratings.py:206-212` | `SELECT ... FROM marts.dim_wines LEFT JOIN marts.wine_ratings_vivino ... WHERE vivino.pk_wine IS NULL LIMIT 15` — i.e. only 15 unmatched wines are attempted per DAG run |
| 6. dbt source | `godvinkaup_dbt/models/marts/schema.yml:4-7` | `source('marts','wine_ratings_vivino')` |
| 7. Marts (wines) | `godvinkaup_dbt/models/marts/wines.sql:103-105` | **Inner join** `dim_wines.id = wine_ratings_vivino.pk_wine` — see vivino-dependency-map.md |
| 8. Ranking | `wines.sql:51-84` | `rating`/`rating_count` → `recommendation` |
| 9. Text | `wines_to_embed.sql:45-56` | `rating` thresholds → Icelandic quality adjectives in `text_to_embed` |
| 10. Export/embed | same as above | `export_wines_to_json.py:14` (`rating > 3.4`), `embed_wines.py:59` (`recommendation >= 0.5`) |

## Consolidated Mermaid lineage diagram (field-level)

```mermaid
flowchart LR
    subgraph ATVR_SRC[vinbudin.is]
        A1["ProductID, ProductName,\nProductPrice, ProductYear, ..."]
    end
    subgraph SANTE_SRC[sante.is]
        S1["Shopify product JSON:\ntitle, vendor, tags, variants"]
    end
    subgraph UVA_SRC[uvavino.is]
        U1["WooCommerce product JSON:\nattributes, tags, categories"]
    end
    subgraph VIVINO_SRC[vivino.com search]
        V1["JSON-LD: name, manufacturer,\naggregateRating.ratingValue/reviewCount"]
    end

    A1 -->|scrape_{red,white,rose,sparkling}_wines.py| L_A["landing.{red,white,rose,sparkling}_wines\n(id,name,volume,price,producer,...)"]
    S1 -->|scrape_sante_wines.py| L_S["landing.sante_wines\n(id,name,price,producer,country,...)"]
    U1 -->|scrape_uva_wines.py| L_U["landing.uva_wines\n(wine_id='UVA'+id, name, price,...)"]
    V1 -->|scrape_vivino_ratings.py + score_match| L_V["marts.wine_ratings_vivino\n(pk_wine,vivino_id,rating,rating_count,\nname_score,producer_score)"]

    L_A --> STG["stg_all_wines (intermediate)\nUNION ALL, field mapping"]
    L_S --> STG
    L_U --> STG

    STG --> DIM["dim_wines (marts)\nincremental, id, valid flag"]
    DIM -->|"dim_wines.id = pk_wine\n(INNER JOIN)"| WINES["wines (marts)\nrating, rating_count, vivino_id,\nrecommendation = f(rating, rating_count, price, volume, is_organic)"]
    L_V -->|"INNER JOIN"| WINES

    WINES --> EMBED["wines_to_embed (marts)\ntext_to_embed w/ rating-based Icelandic phrasing"]
    WINES -->|"WHERE rating > 3.4"| JSONOUT["wines_json.json"]
    EMBED -->|"WHERE recommendation >= 0.5"| QDRANT["Qdrant: wines_embeddings\npayload incl. rating, rating_count, link_vivino"]
    JSONOUT --> GH["push_gv_to_github.py"] --> WEBSITE[["External repo:\nSlaterinn/godvinkaup"]]
```
