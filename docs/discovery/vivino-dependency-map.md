# Vivino Dependency Map (Verified)

Search scope: case-insensitive match for `vivino|rating|ratings|rating_count|ratings_count|
vivino_rating|vivino_id|vivino_url|wine_id|score|3.6|3,6` across `*.py`, `*.sql`, `*.yml`,
`*.yaml`, `*.md`, `*.csv`, `*.json`, repo-wide (excluding `.git`). Files matched:

```text
dags/gv_scrape_vivino.py
dags/scripts/scrape_vivino_ratings.py
dags/scripts/embed_wines.py
dags/scripts/export_wines_to_json.py
dags/scripts/fix_atvr_links.py
dags/scripts/scrape_atvr_descriptions.py
dags/scripts/scrape_uva_wines.py
docker-compose.yml                                       (matches "score/rating" only via unrelated .env comment text — not a Vivino dependency)
godvinkaup_dbt/dbt_project.yml                            (matches "score" only inside the word "organization's" — false positive, not a Vivino dependency)
godvinkaup_dbt/models/intermediate/stg_all_wines.sql      (matches "wine" tokens only — no Vivino dependency)
godvinkaup_dbt/models/marts/schema.yml
godvinkaup_dbt/models/marts/wines.sql
godvinkaup_dbt/models/marts/wines_to_embed.sql
dags/fantrax_ingestion.py, dags/scripts/fantrax/*         (Fantrax "player scoring" — unrelated domain, false positive on "score")
```

The `fix_atvr_links.py` and `scrape_atvr_descriptions.py` / `scrape_uva_wines.py` matches are all
on the generic token `wine_id`/`rating` used for unrelated ATVR/Uva fields, not Vivino — confirmed
by reading each file; they carry no Vivino dependency and are excluded from the table below.

No occurrences of `3.6`, `3,6`, `vivino_url`, or `ratings_count` (plural) were found as literal
tokens; the literal `3.6` rating threshold appears written as `3.6` inside a SQL string comparison
(`wines_to_embed.sql:55`), covered below.

## Dependency table

| File | Line / object | Dependency type | Input field | Output field | Downstream consumer | Removal impact | Recommended disposition | Confidence |
|---|---|---|---|---|---|---|---|---|
| `dags/gv_scrape_vivino.py:15-29` | DAG `godvinkaup_scrape_vivino` | Acquisition | (HTTP scrape) | `marts.wine_ratings_vivino` rows | `godvinkaup_dbt_run` (indirectly, via source table) | Disabling this DAG freezes `wine_ratings_vivino`; no new rows are ever inserted | Keep, but decouple ranking logic from Vivino before treating this as optional | High |
| `dags/scripts/scrape_vivino_ratings.py:14-19` | hardcoded DB connection | Acquisition (config) | — | psycopg2 connection | entire Vivino script | N/A to removal, but blocks safely disabling/rotating credentials for just this pathway | Move to Airflow connection / secret; see technical-debt-register | High |
| `dags/scripts/scrape_vivino_ratings.py:85-110 fetch_vivino_results` | Acquisition | wine name (query) | raw JSON-LD from vivino.com search | `select_best_match` | Wines with no page found are simply skipped (`process_wine_item` returns early, line 161) — silent gap, not an error | Log a metric/row for "no match" instead of silent `return` | High |
| `dags/scripts/scrape_vivino_ratings.py:112-125 score_match` | Identity/matching | `name_lookup`, `producer_query` vs scraped `name`/`manufacturer.name` | `name_score`, `producer_score` (SequenceMatcher ratio) | `select_best_match`, then persisted to `wine_ratings_vivino.name_score/producer_score` | Fuzzy-match quality directly controls whether a wine is confidently linked to a Vivino product; no confidence threshold is enforced before insert (see next row) | Add a minimum combined-score gate before insert, or surface `verified` (currently always `NULL`, line 192) as an actual QA flag | High |
| `dags/scripts/scrape_vivino_ratings.py:142` `select_best_match` | Identity/matching | candidate scores | `best_index` | inserted row | A match with `total_score` just above 0.5 is accepted with no manual review path; `verified` column exists but is always inserted as `NULL` (line 192) | Wire up `verified` or drop the column if truly unused | High |
| `dags/scripts/scrape_vivino_ratings.py:61-78 insert_bridge_wine` | Acquisition / transformation | `wine_id, vivino_id, name, producer, url, rating, rating_count, image_url, name_score, producer_score` | `marts.wine_ratings_vivino` row (upsert on `pk_wine`) | `godvinkaup_dbt/models/marts/schema.yml` source, `wines.sql` | This is the sole writer of the table `wines.sql` inner-joins against | Document/track the table's DDL in this repo (currently undiscoverable — see architecture doc §5) | High |
| `godvinkaup_dbt/models/marts/schema.yml:4-7` | Documentation | — | — | dbt source doc for `wine_ratings_vivino` | Confirms dbt's own understanding that this is "External table with Vivino wine ratings" | Keep as living documentation; expand with freshness/test config | High |
| `godvinkaup_dbt/models/marts/wines.sql:103-105` | **Identity/matching + quality-filter** | `dim_wines.id = wine_ratings_vivino.pk_wine`, `INNER JOIN` | row inclusion in `marts.wines` | `wines_to_embed`, `embed_wines.py`, `export_wines_to_json.py`, website JSON | **Critical**: any wine without a Vivino match is silently excluded from the mart and every downstream artifact — not nulled, removed entirely | If Vivino match is meant to be optional/enrichment, change to `LEFT JOIN` and add explicit null-handling for rating-dependent fields downstream | High |
| `godvinkaup_dbt/models/marts/wines.sql:9,36,41,93-97` | Export-contract / presentation | `vivino_id`, `producer` (as `producer_vivino`), `wine_url` (as `link_vivino`), `rating`, `rating_count` | same-named mart columns | website JSON export, Qdrant payload | These columns are exported verbatim to the website; removing Vivino leaves no substitute source for them | Decide product-level fallback (e.g. omit column vs. blank) before decoupling | High |
| `godvinkaup_dbt/models/marts/wines.sql:51` | Ranking / transformation | `vino.rating` | `rating_adjusted = power(rating, 3.8)` | `recommendation` calculation | Core ranking signal is a stark exponential (`^3.8`) of the raw 0–5 Vivino star rating — small rating differences produce very large score swings | Any independent scoring model must either replace this term or explicitly document the change in ranking behavior | High |
| `godvinkaup_dbt/models/marts/wines.sql:52-57` | Ranking / quality-filter | `vino.rating_count` | `rating_count_index` (0.8 / 0.9 / 0.95 / 1.0 tiered multiplier) | `recommendation` calculation | Wines with fewer than 100 Vivino reviews are penalized 20% in score regardless of actual quality — an arbitrary confidence proxy hardcoded from Vivino's review volume | Replace with an explicit, documented confidence-weighting policy if Vivino is removed or supplemented | High |
| `godvinkaup_dbt/models/marts/wines.sql:58-61` | Quality-filter (non-Vivino, listed for context) | `vinbud.is_organic` | `rating_organic_index` (1.1× if organic) | `recommendation` | Not Vivino-derived, but multiplies with the Vivino-derived `rating_adjusted`/`rating_count_index` terms in the same formula | N/A — organic bonus is independent of Vivino | High |
| `godvinkaup_dbt/models/marts/wines.sql:62-84` | **Ranking (core score)** | `volume, price, rating, rating_count, is_organic` | `recommendation` (rounded 0–1 score) | `wines_to_embed`, `embed_wines.py` filter, `wines_to_embed.sql` text | **Every wine's ranking on the site is a deterministic function that requires a non-null Vivino `rating`.** No Vivino rating ⇒ `recommendation` is `NULL` (Postgres `power(NULL, x)` propagates NULL) ⇒ excluded by every downstream `>=` filter | This is the single highest-priority target for an independent scoring model per the project's stated goal | High |
| `godvinkaup_dbt/models/marts/wines_to_embed.sql:45-56` | Presentation / quality-filter (text) | `recommendation`, `rating` | natural-language Icelandic sentence in `text_to_embed`, with **hardcoded literal thresholds `4.2`, `4`, `3.8`, `3.6`** on the raw Vivino 0–5 scale | OpenAI embedding text, therefore semantic search/RAG results in `wines_embeddings` | The literal `3.6` threshold in the prompt's search list is exactly this line (`... when rating >= 3.6 then 'ágæt' ...`) | These thresholds assume Vivino's specific 0–5 star scale; a different scoring model's scale would silently produce wrong Icelandic quality adjectives unless this block is rewritten | High |
| `dags/scripts/embed_wines.py:59` | Quality-filter | `marts.wines_to_embed.recommendation` | row inclusion for embedding | Qdrant `wines_embeddings` collection | `WHERE recommendation >= 0.5` — since `recommendation` requires Vivino rating, wines without a Vivino match never reach Qdrant either | Indirect Vivino dependency; document explicitly since it's easy to miss (no literal "vivino" token on this line) | High |
| `dags/scripts/embed_wines.py:53,57-58` | Export-contract | `link_vivino`, `rating`, `rating_count` | Qdrant point payload | any consumer of the Qdrant collection (semantic search backend) | Same fields as the website export, duplicated into a second consumer | Keep both export paths in sync if the contract changes | High |
| `dags/scripts/export_wines_to_json.py:14` | **Quality-filter + export-contract** | `marts.wines.rating` | row inclusion for `wines_json.json` | website (`Slaterinn/godvinkaup` repo, external) | `WHERE rating > 3.4` — a second, independent hardcoded Vivino-scale threshold gating the website; largely redundant with the inner join above but adds its own cutoff | Centralize the "what counts as good enough to publish" threshold in one place (currently duplicated as an inner-join requirement *and* a `>3.4` filter *and* text-generation breakpoints) | High |
| `godvinkaup_dbt/models/marts/schema.yml:93-97,75-76,90-91,19-21` | Documentation/test | column docs for `rating`, `rating_count`, `producer_vivino`, `link_vivino`, `vivino_id` | — | dbt docs site (if generated) | Confirms provenance in documentation but **no dbt tests** exist on any of these columns (no `not_null`, no range check, no freshness test) | Add `not_null`/accepted-range tests plus a `dbt source freshness` block on `wine_ratings_vivino` | High |

## What exactly stops working if Vivino acquisition is disabled today?

Disabling the `godvinkaup_scrape_vivino` DAG does **not** fail loudly anywhere in the pipeline — it
fails silently and cumulatively:

1. `marts.wine_ratings_vivino` stops receiving new/updated rows immediately; existing rows keep
   their last-scraped `rating`, `rating_count`, and `image_url` forever (no expiry logic exists on
   that table).
2. `marts.wines` (`godvinkaup_dbt/models/marts/wines.sql:103-105`) requires an **inner join** match
   against that table. Any wine that is new in `landing`/`dim_wines` after Vivino acquisition stops
   — or any wine that was never successfully matched (fuzzy-match failures, `LIMIT 15`-per-run
   backlog, `select_best_match` returning nothing) — is **excluded from the mart entirely**, not
   given a null rating. The wine simply never appears in `marts.wines`.
3. Because `recommendation` (the core price/quality ranking score) is `power(vino.rating, 3.8) *
   ...` (`wines.sql:62-84`), it is undefined for any row that *did* enter via a stale match once its
   `rating` becomes suspect, and is entirely absent for every wine that never matched. Ranking
   quietly degrades to only the ever-shrinking set of previously Vivino-matched wines.
4. `dags/scripts/embed_wines.py:59` (`WHERE recommendation >= 0.5`) and
   `dags/scripts/export_wines_to_json.py:14` (`WHERE rating > 3.4`) both hard-require that
   Vivino-derived value, so the Qdrant semantic-search index and the public website JSON both stop
   receiving new wines too.
5. Nothing in the pipeline raises an error, sends an alert, or fails a task when this happens —
   there is no row-count check, no dbt test, no freshness assertion anywhere in this repo that
   would catch "Vivino stopped supplying data." The system would appear to run green in Airflow
   while the visible wine catalog on the website slowly stops growing and, as ÁTVR/Sante/Uva rotate
   their assortments and `dim_wines.valid` flips old rows to `0`, could shrink over time.

In short: **removing Vivino does not merely remove optional enrichment — it silently caps the
entire product catalog at whatever was already Vivino-matched, and freezes the ranking model that
the website and the recommendation/embedding pipeline both depend on.**
