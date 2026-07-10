# Initial Scoring-System Readiness (Verified)

This assesses what an **independent** wine-scoring model (i.e. one not solely derived from
Vivino) could draw on today, based only on fields verifiably present in `landing.*` sources,
`stg_all_wines`, `dim_wines`, and `wines`. It does not propose the scoring model itself.

Availability classes used: **structured & reliable**, **structured but inconsistent**, **free-text
only**, **obtainable from an existing source (not yet extracted)**, **absent**.

| Signal | Availability | Current source(s) | Quality notes | Normalization needed | Major gap |
|---|---|---|---|---|---|
| Producer | Structured but inconsistent | `landing.red/white/rose/sparkling_wines.producer` (ÁTVR `ProductProducer`), `landing.sante_wines.producer` (Shopify `vendor`), `landing.uva_wines.producer` (WooCommerce attribute `[13,116]` or tag `[721]`) | Three independently-sourced free-text producer strings, no shared producer identity/dictionary; `wines.sql:36` also carries `producer_vivino` as a second, Vivino-scraped producer string with no reconciliation logic beyond the original fuzzy match | Yes — producer-name canonicalization/dedup across ÁTVR/Sante/Uva/Vivino spellings | No canonical producer entity exists anywhere in the schema |
| Winemaker | Absent | — | Not scraped from any of the 4 sources | — | Would require a new source (e.g. producer website, critic database) |
| Region | Structured but inconsistent | `origin_place`/`origin_district`/`area` fields across all 3 retailer sources, each with its own vocabulary; Sante additionally infers country from a hardcoded `wine_country_map` region-name lookup (`scrape_sante_wines.py:22-55`) when the tag-based country is `N/F` | Icelandic-labeled, inconsistent granularity (ÁTVR splits `origin_place`/`origin_district`, Uva has `area`, Sante has `area`/`district`) | Yes — a shared region/appellation hierarchy across sources | No appellation-level classification (e.g. AOC/DOCG) beyond free-text region name |
| Country | Structured but inconsistent | Same fields as above; `wines.sql:15-18` normalizes casing (`Óskráð` for missing) but not underlying values across sources | Spelling/casing varies (`bandaríkin` vs `Bandaríkin` vs `USA`) — see `stg_all_wines.sql:298-300` ad hoc fixes for Uva only | Yes | Country lookup logic is duplicated/inconsistent per source (Sante has its own map, Uva has its own `CASE`, ÁTVR has none) |
| Appellation / classification (AOC, DOCG, etc.) | Absent | — | No field carries a formal appellation/classification tier; `origin_district`/`area` are informal place names only | — | Would need new extraction (retailer descriptions sometimes mention this in free text — see "Retailer description" row) or a new source |
| Vintage | Structured but inconsistent | `produced_year` (ÁTVR: `ProductYear`; Sante: parsed from title regex or tag heuristic, `scrape_sante_wines.py:160-172`; Uva: regex on product name, `scrape_uva_wines.py:88-90`) | Sante/Uva vintage extraction is regex/heuristic-based over free text, not a structured field from the source API — real miss risk (e.g. Sante falls back to "any tag that parses as an int within 30 years of current year," `scrape_sante_wines.py:166-172`) | Yes — confidence flag recommended given heuristic extraction | No non-vintage/NV flag beyond "0" default in some paths |
| Grapes | Free-text / structured but inconsistent | `grapes` field across all 3 sources (ÁTVR: `ProductWine` attribute; Sante: matched against a scraped filter taxonomy via normalized-string matching, `scrape_sante_wines.py:202-208`; Uva: WooCommerce attribute `[7]` or tag `[116]`) | Comma-joined multi-grape strings, no cardinality/percentage information, inconsistent separators (`,` vs `;` after `stg_all_wines.sql` remapping) | Yes — split into a grape/wine junction table with normalized grape names | No blend-percentage data anywhere |
| Wine style (still/sparkling/fortified, sweetness, body) | Structured but inconsistent | `category` (Red/White/Rose/Sparkling Wine, mapped per-source in `stg_all_wines.sql`), plus `taste_group` decoded into `sweetness`/`boldness` in `wines.sql:87-100` from ÁTVR's proprietary taste-group codes only (Sante/Uva always get `'N/F'` for `taste_group`, so `sweetness`/`boldness` are `'N/F'` for every non-ÁTVR wine) | ÁTVR-only signal; **not populated for Sante or Uva wines at all** | Yes — would need an independent style classifier if Sante/Uva coverage matters | No fortified/dessert-wine flag beyond the ÁTVR "Eftirréttarvín" taste-group case |
| Price | Structured and reliable | `price` across all 3 sources, all in ISK | Directly usable; already load-bearing in the existing `recommendation` formula (`wines.sql:64,72`, `volume / sqrt(price)`) | Minor — confirm currency is always ISK (verified: all 3 scrapers assume ISK, no currency field is carried) | None significant |
| Bottle size | Structured but inconsistent | `volume` (ÁTVR: `ProductBottledVolume`; Sante: parsed ml/cl from title/tags, default 750, `scrape_sante_wines.py:174-189`; Uva: parsed from product name, default 750, `scrape_uva_wines.py:78-85`) | `wines.sql:108` filters to `volume in (0, 750)` only — **any non-750ml/other bottle size is excluded from the mart entirely**, a second silent-exclusion pattern beyond the Vivino inner join | Low | Half-bottles/magnums are dropped from the catalog by this filter, not merely mis-scored |
| Awards | Absent | — | No source scrapes competition medals/awards (Decanter, IWSC, etc.) | — | Would require a new external source entirely |
| Critic reviews (professional, e.g. Wine Spectator/Robert Parker style) | Absent | — | Only Vivino's crowd-sourced `rating`/`rating_count` exists; no professional critic score is scraped | — | This is the core gap an independent scoring model is presumably meant to address |
| Retailer description | Free-text only | `description` (ÁTVR via `scrape_atvr_descriptions.py`, upserted into `landing.atvr_wine_descriptions`; Sante via `body_html`→stripped text, `scrape_sante_wines.py:154-156`; Uva has none — `uva_wines` CTE hardcodes `'N/A' as description`, `stg_all_wines.sql:323`) | Retailer marketing copy, Icelandic/English mixed, unstructured; ÁTVR descriptions are only backfilled for wines missing one (`scrape_atvr_descriptions.py:102-135`), so coverage/freshness is uneven | Yes — would need NLP extraction (grape %, tasting notes, awards mentions) to become structured | Uva coverage is zero |
| Tasting notes | Free-text only, entangled with "Retailer description" | Same `description` field; no separate structured tasting-note field (aroma/palate/finish) exists | Same caveats as above | Yes | No structured sensory attributes anywhere |
| Importer | Absent | — | No importer/distributor field is scraped from any of the 3 retailers | — | Would require a new source or retailer-page field not currently captured |
| Retailer / seller | Structured and reliable | `seller` hardcoded per scraper (`"ÁTVR"`, `"Sante"`, `"Uva"`) | Reliable but only 3 possible values, hardcoded as string literals in code rather than a lookup/dimension table (see technical-debt-register TD-06 context) | None functionally, but consider a `dim_seller` table if more retailers are added | None significant today |
| Organic / production designation | Structured but narrow | `is_organic` (ÁTVR: `ProductOrganic`; Sante: hardcoded `'true'` for every row, `stg_all_wines.sql:284` — **not actually scraped from Sante**, always true; Uva: hardcoded `'true'` for every row, `stg_all_wines.sql:319` — **also not actually scraped from Uva**) | Only ÁTVR's `is_organic` is a genuine per-wine signal; Sante and Uva's values are constants, not real data, and currently feed a genuine +10% score multiplier (`wines.sql:58-61`) for every Sante/Uva wine regardless of truth | Critical fix needed — this is a data-quality bug (not just a normalization gap): Sante/Uva wines are unconditionally receiving the organic bonus | Confirm with Sante/Uva source data whether an organic flag is actually obtainable; if not, remove the blanket `'true'` |

## Summary for scoring-model planning

**Reliable structured foundation today:** price, bottle size (subject to the 750ml filter bug),
seller/retailer, and (ÁTVR-only) sweetness/boldness/organic status.

**Usable but needs normalization work:** producer, country, region/origin, grapes, vintage — all
present across sources but with per-source vocabularies, heuristic extraction (especially
vintage), and no shared identity keys.

**The largest gaps for an independent scoring model** are: (1) no professional critic score of any
kind exists anywhere in the pipeline — the *only* quality signal today is Vivino's crowd rating;
(2) no awards/competition data; (3) no importer data; (4) tasting notes exist only as unstructured
retailer marketing copy with uneven per-source coverage (absent entirely for Uva); (5) the schema
has no conceptual "wine" entity distinct from a retailer listing (see technical-debt-register
TD-16), so any new score must first decide what grain it scores at; (6) the Sante/Uva
`is_organic='true'` hardcoding (this table, row "Organic / production designation") is actively
feeding incorrect information into the existing `recommendation` formula today and should be fixed
regardless of what replaces or supplements Vivino.
