# Technical Debt Register (Verified)

Severity scale: Critical, High, Medium, Low, Informational. Secret values are never reproduced
below — only file, line, and exposure type.

---

### TD-01 — Hardcoded plaintext database credentials committed to Git (multiple, inconsistent)
**Severity:** Critical
**Category:** Secrets / credential management
**Evidence:** `dags/scripts/scrape_vivino_ratings.py:14-19` (`psycopg2.connect(host="192.168.86.226", port=5433, database="godvinkaup", user="postgres", password=<literal>)`); `dags/scripts/scrape_sante_wines.py:9-15` and `dags/scripts/scrape_sante_filters.py:15-21` (same host, a **different** literal password). These bypass the Airflow connection (`postgres_conn_id="postgres_godvinkaup"`) used correctly elsewhere (e.g. `scrape_uva_wines.py:97`, `export_wines_to_json.py:10`, `fix_atvr_links.py:88`).
**Operational impact:** Credentials are permanently in Git history even if rotated later; two different passwords for the same host/db suggest at least one is stale or a typo risk; any clone of this repo leaks working database access.
**Recommended remediation:** Rotate both credentials immediately; migrate all three scripts to `PostgresHook(postgres_conn_id="postgres_godvinkaup")`; add a pre-commit secret-scanning hook (`detect-secrets` or similar) to prevent recurrence.
**Suggested phase:** Immediate (pre-scoring-work).

### TD-02 — Hardcoded GitHub token literal in `docker-compose.yml`
**Severity:** Critical
**Category:** Secrets committed to Git
**Evidence:** `docker-compose.yml:63`, `GITHUB_TOKEN: <literal token value>` inside `x-airflow-common.environment`.
**Operational impact:** A working GitHub token (used by `push_gv_to_github.py` to write to `Slaterinn/godvinkaup`) is exposed to anyone with read access to this repository's history.
**Recommended remediation:** Revoke/rotate the token now; remove the literal from `docker-compose.yml` and source it from `.env` (already `.gitignore`d — see `.gitignore:69-71`) or an Airflow Variable, matching the pattern `push_gv_to_github.py:8` already expects (`os.environ.get("GITHUB_TOKEN") or Variable.get(...)`).
**Suggested phase:** Immediate.

### TD-03 — Live session cookies/tokens committed in `dags/fantrax_ingestion.py`
**Severity:** Critical
**Category:** Secrets committed to Git
**Evidence:** `dags/fantrax_ingestion.py:16-45`, dict literal `FANTRAX_COOKIES` containing session/Cloudflare-clearance-style cookie values, with an inline comment "(TEMPORARY) Later: move to Airflow Variables or a secrets backend."
**Operational impact:** Not wine/Vivino-related, but shares this repository and CI; same exposure class as TD-01/02. Session cookies expire but the pattern (hardcoding auth material in DAG source) will recur.
**Recommended remediation:** Follow the file's own TODO — move to Airflow Variables/Secrets backend before the next Fantrax change.
**Suggested phase:** Immediate, tracked separately from wine-scoring work since it's a different domain.

### TD-04 — `marts.wine_ratings_vivino` has no DDL tracked anywhere in this repo
**Severity:** High
**Category:** Schema drift risk / missing provenance
**Evidence:** `dags/scripts/scrape_vivino_ratings.py:61-78` only ever `INSERT ... ON CONFLICT (pk_wine) DO UPDATE` into `marts.wine_ratings_vivino`; no `CREATE TABLE` for it exists in this repo (contrast with `landing.uva_wines`, `landing.sante_wines`, `landing.red_wines`, etc., which are all explicitly `CREATE TABLE`d by their scrapers). It is declared only as a dbt `source` (`godvinkaup_dbt/models/marts/schema.yml:4-7`).
**Operational impact:** The table's real schema (column types, the unique constraint implied by `ON CONFLICT (pk_wine)`) lives only in the live database. A fresh environment cannot be provisioned from this repo alone; any manual schema change is invisible to code review.
**Recommended remediation:** Add DDL (as a dbt seed-adjacent script, an idempotent migration, or at minimum a documented `CREATE TABLE IF NOT EXISTS` in the scraper, matching the pattern the other scrapers already use) and commit it.
**Suggested phase:** Before building the new scoring model, since it will likely need to alter or extend this table.

### TD-05 — `marts.wines.sql` INNER JOINs Vivino instead of LEFT JOIN
**Severity:** High
**Category:** Correctness / silent data loss
**Evidence:** `godvinkaup_dbt/models/marts/wines.sql:103-105`.
**Operational impact:** Documented at length in `vivino-dependency-map.md`; repeated here because it is the single highest-impact defect in the pipeline — it silently caps the catalog and couples ranking to Vivino availability with no failure signal.
**Recommended remediation:** Decide product intent (should unmatched wines appear without a score?) before changing; if yes, switch to `LEFT JOIN` and add explicit null-safe handling in `recommendation`/`text_to_embed`.
**Suggested phase:** Design decision required before/alongside the new scoring model (this is precisely what an independent score would let you fix).

### TD-06 — Duplicated scraper logic across 4 near-identical files
**Severity:** Medium
**Category:** Duplication / maintainability
**Evidence:** `dags/scripts/scrape_{red,white,rose,sparkling}_wines.py` are ~95% identical (same `parse_date_on_market`, `create_product_link`, `str_to_int`, `recreate_staging_table`, `fetch_and_insert_*`, and identical `psycopg2.extras.execute_batch` call), differing only in `category`/table name/`params["category"]`. The same `CASE WHEN container_type = ...` and `CASE WHEN taste_group = ...` translation tables are then duplicated a **second** time, 4×, in `godvinkaup_dbt/models/intermediate/stg_all_wines.sql:18-53,80-115,143-178,206-241`.
**Operational impact:** A fix or schema change (e.g. new `taste_group` code from ÁTVR) must be applied in 4 Python files and 4 SQL CTEs — 8 places total; already a source of drift risk (the two backup/legacy connection strings in TD-01 show this pattern of forked duplicates diverging).
**Recommended remediation:** Parameterize the scraper into one function taking `category`/`table_name`; extract the taste_group/container_type mapping into a dbt seed or macro referenced once from `stg_all_wines.sql`.
**Suggested phase:** Medium-term cleanup, independent of scoring work; low risk, moderate payoff.

### TD-07 — Stale/orphaned dbt and Airflow scaffolding
**Severity:** Low
**Category:** Dead code / repository hygiene
**Evidence:** `godvinkaup_dbt/macros/_generate_schema_name.sql.bak` (backup file, superseded by `generate_schema_name.sql`); `godvinkaup_dbt/models/example/{my_first_dbt_model.sql,my_second_dbt_model.sql,schema.yml}` (dbt-init starter models, not referenced by any wine or Fantrax model); `dags/test_dbt_simple_dag.py` (references `/opt/airflow/example_dbt_project`, a path that does not exist in this repo, and the deprecated `airflow.operators.bash_operator` import); `dags/test_dbt_simple2_dag.py` (references dbt models `model1..model4` that do not exist anywhere in `godvinkaup_dbt/models`).
**Operational impact:** These DAGs would fail immediately if ever unpaused/triggered (`catchup`-less manual/daily test DAGs pointing at nonexistent projects/models). They add noise to the Airflow DAG list and to `make validate-airflow`'s `airflow dags list` output.
**Recommended remediation:** Delete `.bak` file, `models/example/`, and both test DAGs, or move them to a clearly-marked `examples/` path excluded from DAG discovery — per AGENTS.md, flag for confirmation before removing since this task is read-only and removal is a judgment call for the maintainer.
**Suggested phase:** Low-risk cleanup, anytime.

### TD-08 — Inconsistent / deprecated Airflow API usage
**Severity:** Medium
**Category:** Framework hygiene
**Evidence:** `airflow.utils.dates.days_ago` used in every production wine DAG (see architecture doc §3); `airflow.hooks.postgres_hook.PostgresHook` (legacy path) mixed with `airflow.providers.postgres.hooks.postgres.PostgresHook` (current path) across sibling scripts; `airflow.operators.bash_operator.BashOperator` (legacy) in the two stale test DAGs vs. `airflow.operators.bash.BashOperator` (current) in `godvinkaup_dbt.py`.
**Operational impact:** Legacy import paths are deprecation-warning-noisy today and are removal candidates in future Airflow major versions; inconsistency makes it unclear which pattern is "current" for new DAGs.
**Recommended remediation:** Standardize on `pendulum` static start dates and the `airflow.providers.postgres...` import path repo-wide; document the standard in `docs/airflow.md` (currently empty).
**Suggested phase:** Medium-term, batch with an Airflow version upgrade.

### TD-09 — No enforced inter-DAG dependency between extraction and `dbt run`
**Severity:** High
**Category:** Orchestration correctness
**Evidence:** `dags/godvinkaup_dbt.py:34-59` — three `PythonSensor` definitions that would wait for `godvinkaup_extract_atvr/sante/uva` to succeed same-day are fully commented out; the `dbt run` task runs unconditionally at `15 10 * * *`, only 15 minutes after the 10:00 extraction DAGs start.
**Operational impact:** If any extraction DAG runs long (network slowness, retailer site slowness, retries firing), `dbt run` executes against partially-updated or stale `landing` tables with no warning. This is a timing race, not a guaranteed sequence.
**Recommended remediation:** Re-enable the sensors, or better, migrate to Airflow Datasets/`ExternalTaskMarker` for explicit, version-appropriate cross-DAG dependencies.
**Suggested phase:** High priority — cheap fix, meaningful reliability gain.

### TD-10 — No dbt tests or source-freshness checks on Vivino-derived data
**Severity:** High
**Category:** Data quality / observability
**Evidence:** `godvinkaup_dbt/models/marts/schema.yml` documents `rating`, `rating_count`, `vivino_id`, `producer_vivino`, `link_vivino` but attaches **zero** tests to any of them (only `pk_wine` gets `not_null`/`unique`, `models/intermediate/schema.yml` only tests `wine_food_pairings.id_wine`). No `source freshness` block exists for the `marts.wine_ratings_vivino` source. `godvinkaup_dbt/tests/` and `snapshots/` directories are empty (`.gitkeep` only) despite being declared in `dbt_project.yml`.
**Operational impact:** Combined with TD-05, there is no automated signal anywhere in the pipeline that would detect Vivino acquisition silently stalling, a rating going out of the expected 0–5 range, or a `dbt run` producing an empty/shrunk `marts.wines`.
**Recommended remediation:** Add `not_null`/`accepted_range` tests on `rating`/`rating_count`, a `dbt source freshness` config on `wine_ratings_vivino`, and a row-count sanity test on `marts.wines` (e.g. `dbt-utils.recency` or a custom singular test).
**Suggested phase:** Should land alongside/before the scoring model, since the model will need reliable inputs.

### TD-11 — No historical tracking (snapshots) despite scaffolding for it
**Severity:** Medium
**Category:** Missing observability / lost history
**Evidence:** `godvinkaup_dbt/dbt_project.yml:19` declares `snapshot-paths: ["snapshots"]`, but `godvinkaup_dbt/snapshots/` contains only `.gitkeep`. `landing.*` tables for ÁTVR/Sante/Uva are `DROP TABLE ... CASCADE` and fully recreated every run (`scrape_red_wines.py:19-47` and siblings), destroying the prior day's raw snapshot with no retention.
**Operational impact:** Price history, rating history, and catalog-availability history are all unrecoverable after each daily run — this directly blocks any future "price trend" or "rating over time" scoring signal, and blocks debugging "why did this wine disappear."
**Recommended remediation:** Introduce dbt snapshots on `dim_wines`/`wines` (or at minimum an append-only price/rating history table) before relying on trend-based signals in a new scoring model.
**Suggested phase:** Should be scoped explicitly as a prerequisite if the scoring model wants any time-series signal (see scoring-data-readiness.md).

### TD-12 — Broad exception handling throughout scrapers
**Severity:** Medium
**Category:** Error handling
**Evidence:** `except Exception as e: print(...)` patterns in `scrape_vivino_ratings.py:106-107,198-199`, `scrape_atvr_descriptions.py:78-79`, `scrape_sante_wines.py:236-237`, `scrape_sante_filters.py:43-45,66-68,105-107`; `dags/scripts/embed_wines.py:133-134` (`except Exception` around the Qdrant upsert, swallowing failures per-batch with just a print).
**Operational impact:** Failures are masked as successful task completion in Airflow (the task doesn't raise, so it's marked green) while individual wines/batches silently fail to load — directly contradicts AGENTS.md's "Handle errors explicitly" and "Use logging instead of `print()`" guidance.
**Recommended remediation:** Narrow exception types where feasible, use `logging` instead of `print`, and re-raise or explicitly count/report failures so Airflow task state reflects partial failure.
**Suggested phase:** Medium-term, alongside TD-06 refactor.

### TD-13 — No dependency manifest for scraper-only libraries
**Severity:** Medium
**Category:** Reproducibility
**Evidence:** `pyproject.toml` contains only `[tool.ruff]` configuration, no `[project.dependencies]`. `Dockerfile:51-62` only explicitly installs `protobuf`, `dbt-postgres`, `openai`, `qdrant-client`, `python-dotenv`. Scrapers import `requests`, `bs4` (BeautifulSoup), and `psycopg2` (`scrape_vivino_ratings.py:8-10`, `scrape_atvr_descriptions.py:8`, etc.) with no visible install step for these in this repo.
**Operational impact:** The exact runtime dependency set is unreproducible from this repository alone; a rebuild of the Docker image is not guaranteed to have the same libraries/versions the current runtime happens to have accumulated.
**Recommended remediation:** Add an explicit `requirements.txt` or `pyproject.toml` dependency list covering `requests`, `beautifulsoup4`, `lxml`, `psycopg2`(-binary), pin versions, and install it in the `Dockerfile`.
**Suggested phase:** Should precede any dependency-sensitive change (e.g. adding a new scraping/matching library for the scoring model).

### TD-14 — Fragile, single-selector HTML scraping
**Severity:** Medium
**Category:** Scraper robustness
**Evidence:** `dags/scripts/scrape_atvr_descriptions.py:60` relies on one hardcoded element id, `span#ctl00_ctl01_Label_ProductDescription`, a classic ASP.NET auto-generated control ID that breaks on any ÁTVR site template change; `scrape_vivino_ratings.py:98` relies on `soup.find("script", type="application/ld+json")` being the first/only such block.
**Operational impact:** A front-end change on either site silently degrades to "N/F"/no-match rather than raising a detectable error (per TD-12, wrapped in broad `except`).
**Recommended remediation:** Add a fallback selector and/or a canary alert when the hit rate for a given scrape drops sharply.
**Suggested phase:** Low urgency until a scrape actually breaks; worth a monitoring hook regardless.

### TD-15 — Retailer product-ID collisions are structurally possible in `dim_wines`
**Severity:** Medium
**Category:** Data-model / key design
**Evidence:** `dim_wines` (`godvinkaup_dbt/models/marts/dim_wines.sql:5`) is `unique_key='id'` over the union of all sellers. Uva prefixes its ID (`"UVA" + product["id"]`, `scrape_uva_wines.py:130`), but ÁTVR (`vinbudin` numeric `ProductID`) and Sante (raw Shopify numeric `pid`, `scrape_sante_wines.py:212`/`insert_wines`) use their raw numeric IDs with no seller prefix.
**Operational impact:** If a Sante Shopify product ID ever numerically collides with a Vínbúðin `ProductID`, `dim_wines`'s incremental merge (`unique_key='id'`) would silently conflate two different retailer listings as one wine.
**Recommended remediation:** Prefix all seller IDs consistently (e.g. `ATVR<id>`, `SANTE<id>`, matching the `UVA<id>` convention already used) before this becomes load-bearing for a scoring model that assumes one row = one listing.
**Suggested phase:** Should be fixed before the scoring model is built on top of `dim_wines`/`wines`, since key correctness underlies everything downstream.

### TD-16 — No distinction between wine-as-product, vintage, retailer listing, and bottle size
**Severity:** High (for scoring-model purposes specifically)
**Category:** Data model
**Evidence:** `dim_wines`/`wines` key on the retailer's own listing ID (`id`); there is no separate `wine_product_id`/`vintage` grouping — a different vintage of the same wine at the same retailer is a wholly distinct, unrelated row, and the same physical wine at two retailers is two unrelated rows joined to Vivino independently (`wine_ratings_vivino.pk_wine` is 1:1 with `dim_wines.id`, i.e. per-listing, not per-conceptual-wine).
**Operational impact:** Directly relevant to Section G/scoring-data-readiness.md: a "critic score"/"model score" built at the wine-product level has no natural grain to attach to in the current schema; today's Vivino match is effectively a per-retailer-listing lookup that happens to often correspond to one wine.
**Recommended remediation:** Introduce an explicit conceptual "wine" entity (name+producer+vintage, normalized) that `dim_wines` rows map onto many-to-one, before layering a scoring model that should score a wine once, not once per retailer listing.
**Suggested phase:** Foundational — recommend resolving as part of the scoring-model design phase, not as a side effect.

### TD-17 — CI does not validate Airflow DAGs or dbt models
**Severity:** Low
**Category:** CI coverage gap
**Evidence:** `.github/workflows/ci.yml` runs only `ruff format --check`, `ruff check`, and `pre-commit run --all-files`; it never runs `dbt parse`/`dbt compile` or `airflow dags list` (both of which `AGENTS.md` and `scripts/validate_*.sh` describe as the standard validation, but only as local/runtime-repo commands, not in CI).
**Operational impact:** A DAG import error (like the two stale test DAGs already carry) or a broken `ref()`/`source()` in dbt would not be caught until someone runs `make validate` manually or the runtime repo is synced.
**Recommended remediation:** Add a CI job that spins up a minimal dbt profile (or uses `dbt parse` without a live DB) and an Airflow DAG-import smoke test.
**Suggested phase:** Medium-term, improves safety net for all future changes including scoring-model work.

### TD-18 — `verified` column in `wine_ratings_vivino` is written but never populated
**Severity:** Low
**Category:** Dead/no-op field
**Evidence:** `scrape_vivino_ratings.py:192` inserts `None` (Python `None`) as the `verified` value on every row, unconditionally.
**Operational impact:** Any downstream assumption that `verified` reflects manual/automatic QA is false; the column currently carries no information.
**Recommended remediation:** Either wire it to the `name_score`/`producer_score` confidence gate (see TD-01's sibling row in vivino-dependency-map.md) or remove it until it's meaningful.
**Suggested phase:** Cheap, bundle with TD-04's schema work.
