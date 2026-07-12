# Scoring Evidence Inventory

## Purpose

This document catalogues every signal that could plausibly contribute to an independent
wine-scoring system for Godvinkaup — one that does not depend solely on Vivino's crowd rating,
per the gap identified in `docs/discovery/scoring-data-readiness.md` and
`docs/discovery/vivino-dependency-map.md`.

**This is an inventory, not a formula.** It does not propose weights, thresholds, or a scoring
function. Its job is to establish, signal by signal, what evidence exists, how trustworthy it is,
and what *kind* of question it can answer — before anyone decides how to combine it. Any future
scoring design should trace back to a row in this table; if a proposed weight can't be justified by
a signal documented here, that's a sign the inventory needs updating first.

Facts about current repository state are grounded in the discovery documents
(`docs/discovery/current-etl-architecture.md`, `vivino-dependency-map.md`,
`scoring-data-readiness.md`, `data-lineage.md`, `technical-debt-register.md`) and, where those
didn't already cover a field, direct inspection of the scrapers and dbt models. Everything else
(why a signal matters, its reliability class, legal exposure, misleading potential) is scoring-domain
judgment, not a repository fact, and should be revisited as the model design matures.

## Three questions a score must answer

Every signal below is assessed against three distinct questions a scoring system needs to answer.
Conflating them is the single biggest risk in wine-scoring design (see the "misleading signals"
section), so they're kept separate throughout:

- **Quality** — how good is this wine, on its own merits?
- **Confidence** — how much should we trust our quality estimate for *this* wine? (Thin evidence
  should produce a wide error bar, not a suppressed or boosted score.)
- **Value** — given the quality estimate, is the price good or bad? Value is a *relationship*
  between quality and price, never an input to quality itself.

A fourth outcome, **None**, means the signal is useful for filtering, display, or UX, but should not
feed a score at all.

## Column definitions

| Column | Meaning |
|---|---|
| What it measures | The concrete fact or attribute the signal captures. |
| Why it matters | The mechanism by which it plausibly relates to quality, confidence, or value. |
| Possible data sources | Where this could be obtained, in principle — not limited to what's scraped today. |
| Current availability | What exists in this repository today, grounded in the discovery docs and source inspection. |
| Structured / unstructured | Whether the raw signal is machine-parseable today or requires text extraction. |
| Deterministic / AI-assisted | Whether obtaining or normalizing it is a fixed rule/lookup, or requires a model (NLP, entity resolution, LLM extraction) with inherent error rate. |
| Reliability | High / Medium / Low — how much the raw value can be trusted at face value, independent of whether it's structured. |
| Refresh frequency | How often the underlying real-world fact changes (not how often it's currently scraped). |
| Cost to obtain | Engineering/data/API cost to acquire or maintain this signal going forward. |
| Legal / licensing concerns | Scraping ToS, data redistribution, or attribution risk. |
| Explainability | Can this signal be shown to a user as a plain-language reason for the score? |
| Confidence impact | Does the *presence or absence* of this signal change how much we should trust the overall estimate, independent of its own value? |
| Should influence | Quality / Confidence / Value / None — see framework above. |
| Notes | Caveats, current bugs, or open design questions. |

---

## A. Identity & provenance

### Producer

| Attribute | Detail |
|---|---|
| What it measures | The commercial entity that produced/bottled the wine. |
| Why it matters | Producer track record is one of the strongest priors for consistency — a producer that scores well across many wines/vintages predicts quality for a new listing better than any single-bottle signal. |
| Possible data sources | Retailer catalogs, producer websites, Vivino, critic databases (Wine-Searcher, CellarTracker). |
| Current availability | Structured but inconsistent. Present in ÁTVR (`ProductProducer`), Sante (Shopify `vendor`), and Uva (WooCommerce attribute/tag) as three independently-sourced free-text strings, plus a fourth, unreconciled `producer_vivino` string (`wines.sql:36`). No canonical producer entity or dedup logic exists anywhere in the schema. |
| Structured / unstructured | Structured (free-text field), but no shared identity across sources. |
| Deterministic / AI-assisted | Extraction is deterministic; cross-source canonicalization requires fuzzy matching / entity resolution (AI-assisted or rules-based dictionary). |
| Reliability | Medium — each source's raw string is reliable, but without canonicalization, "the same producer" can silently split into multiple track records. |
| Refresh frequency | Rarely changes for an existing listing; effectively static once captured. |
| Cost to obtain | Low to capture; medium to canonicalize (one-time + ongoing maintenance of a producer dictionary). |
| Legal / licensing | None — factual, publicly disclosed attribute. |
| Explainability | High — directly human-readable ("from a producer with N previous 4+ scored wines"). |
| Confidence impact | High — a producer with an established track record materially increases confidence in a new wine's estimate; an unknown producer should widen the error bar. |
| Should influence | Quality (via track record) and Confidence. |
| Notes | Building a canonical producer entity is a prerequisite before this signal can be used at all — today it would silently double- or triple-count the same producer under different spellings. |

### Winemaker

| Attribute | Detail |
|---|---|
| What it measures | The individual (as distinct from the producer/label) responsible for the wine, where notable. |
| Why it matters | For boutique and prestige producers, the winemaker (or consulting oenologist) can be a stronger quality signal than the label itself, especially across producer changes. |
| Possible data sources | Producer websites, press/critic writeups, technical sheets — not typically present in retailer catalogs. |
| Current availability | Absent — not scraped from any of the 4 sources. |
| Structured / unstructured | Would arrive as unstructured text (bios, press) requiring extraction. |
| Deterministic / AI-assisted | AI-assisted (named-entity extraction from text) if pursued. |
| Reliability | Low today (absent); Medium if sourced, since attribution in press coverage is not always current. |
| Refresh frequency | Low — changes infrequently (winemaker tenures span years). |
| Cost to obtain | High relative to value — requires a new source entirely, with sparse coverage (only applies to a minority of wines). |
| Legal / licensing | Low risk — biographical/professional information, generally public. |
| Explainability | High when present ("made by [name], known for..."). |
| Confidence impact | Low overall today given near-total absence; would be a nice-to-have confirmation for a small subset of premium wines. |
| Should influence | Quality (weak, narrow applicability) — practically None today given absence. |
| Notes | Low priority relative to other gaps; revisit only if a premium/boutique tier is built. |

### Winery

| Attribute | Detail |
|---|---|
| What it measures | The physical estate/brand — conceptually distinct from "producer" (legal/bottling entity) in cases like négociant wines, where the winery and the legal producer differ. |
| Why it matters | Distinguishing winery from producer matters for negociant/co-op wines where the bottling entity isn't where the wine was actually made; without the split, track-record attribution can land on the wrong entity. |
| Possible data sources | Same as producer — retailer catalogs, producer sites; the distinction itself is rarely made explicit by any source. |
| Current availability | Absent as a distinct field — only a single `producer` string exists per source, with no winery/négociant distinction (see technical-debt-register TD-16 for the related grain problem). |
| Structured / unstructured | N/A today. |
| Deterministic / AI-assisted | Would require rules (négociant-list lookup) or AI-assisted disambiguation. |
| Reliability | Low — not currently distinguishable from Producer. |
| Refresh frequency | Static. |
| Cost to obtain | Medium — mostly a modeling/schema decision rather than new acquisition, if Producer is later split. |
| Legal / licensing | None. |
| Explainability | Medium — useful nuance for a minority of cases, but adds complexity most users won't need explained. |
| Confidence impact | Low as a standalone signal. |
| Should influence | None today (folded into Producer); Quality/Confidence only if later split out. |
| Notes | Not worth modeling separately until Producer itself is canonicalized — treat as a possible future refinement of Producer, not an independent signal yet. |

### Region

| Attribute | Detail |
|---|---|
| What it measures | The geographic origin below country level (e.g. Rioja, Mendoza, Marlborough). |
| Why it matters | Region carries a weak, aggregate quality prior (climate/terroir/tradition), but that prior applies to *populations* of wines, not individual bottles — see misleading-signals section. |
| Possible data sources | Retailer catalogs, producer labels, appellation registries. |
| Current availability | Structured but inconsistent. `origin_place`/`origin_district`/`area` fields exist across all 3 retailer sources, each with its own vocabulary and granularity (`scoring-data-readiness.md` row "Region"). |
| Structured / unstructured | Structured, but non-canonical vocabulary per source. |
| Deterministic / AI-assisted | Deterministic extraction; canonicalization needs a shared region hierarchy/lookup. |
| Reliability | Medium — raw values are reliable but granularity and spelling vary by source. |
| Refresh frequency | Static. |
| Cost to obtain | Low to capture (already present); medium to build a shared hierarchy. |
| Legal / licensing | None. |
| Explainability | High — human-readable, familiar to wine buyers. |
| Confidence impact | Low to Medium — mostly useful as a weak prior when little else is known. |
| Should influence | Confidence (weak prior filler) more than Quality directly; risk of misuse — see misleading-signals section. |
| Notes | Should never be used alone as a quality driver ("it's from Bordeaux, so it must be good" is exactly the stereotype this system should avoid); more useful combined with Appellation/Classification, which encodes an actual regulatory tier. |

### Country

| Attribute | Detail |
|---|---|
| What it measures | Country of origin. |
| Why it matters | Weakest-resolution geographic prior; mostly useful for filtering/display and very coarse expectations, not scoring. |
| Possible data sources | Retailer catalogs. |
| Current availability | Structured but inconsistent — same source fields as Region; casing/spelling varies across sources (`bandaríkin` vs `Bandaríkin` vs `USA`), with per-source ad hoc fixes rather than a shared lookup (`scoring-data-readiness.md` row "Country"). |
| Structured / unstructured | Structured. |
| Deterministic / AI-assisted | Deterministic (needs a shared normalization lookup, currently duplicated/inconsistent per source). |
| Reliability | Medium — reliable underlying fact, unreliable normalization today. |
| Refresh frequency | Static. |
| Cost to obtain | Low — already present; normalization is a cleanup task, not new acquisition. |
| Legal / licensing | None. |
| Explainability | High. |
| Confidence impact | Low — too coarse to move confidence much on its own. |
| Should influence | None for Quality directly; at most a Confidence/UX filter. |
| Notes | A pure country-level quality prior is a stereotype, not evidence — see misleading-signals section. |

### Appellation / classification (AOC, DOCG, Grand Cru, etc.)

| Attribute | Detail |
|---|---|
| What it measures | A formal, regulated quality/production tier tied to geography and legally-enforced production rules (yield limits, aging requirements, permitted grapes). |
| Why it matters | Unlike raw region or country, an appellation/classification is a legally encoded standard, not just a reputational one — it's a materially stronger prior than "region" alone, because it implies actual constraints on how the wine was made. |
| Possible data sources | Retailer descriptions (mentioned in free text today), regulatory/appellation registries, label parsing. |
| Current availability | Absent — no field carries a formal appellation/classification tier anywhere in the schema; `origin_district`/`area` are informal place names only (`scoring-data-readiness.md` row "Appellation / classification"). |
| Structured / unstructured | Would need new extraction — likely unstructured (buried in retailer descriptions or the wine name itself) until a dedicated source is added. |
| Deterministic / AI-assisted | Extraction from free text is AI-assisted (NLP/regex over descriptions); once extracted, classification against a known tier list is deterministic. |
| Reliability | High once correctly extracted (it's a regulated, verifiable fact) — but extraction reliability from free text is currently unproven for this dataset. |
| Refresh frequency | Static (classifications change on a multi-year/regulatory cadence, e.g. Bordeaux 1855 revisions). |
| Cost to obtain | Medium — requires either new extraction work over existing descriptions or a new reference dataset (appellation registries are largely public). |
| Legal / licensing | Low — appellation systems are public regulatory information. |
| Explainability | High — a well-known, user-legible quality tier ("DOCG," "Grand Cru"). |
| Confidence impact | Medium to High — a verified classification is strong corroborating evidence. |
| Should influence | Quality and Confidence. |
| Notes | One of the highest-leverage gaps identified in `scoring-data-readiness.md`; see top-5 recommendation below. |

---

## B. Composition & vintage

### Vintage

| Attribute | Detail |
|---|---|
| What it measures | The harvest year. |
| Why it matters | Vintage quality varies materially by region and year due to weather (published "vintage charts" exist per region); also needed to correctly interpret ageability and critic scores, which are usually vintage-specific. |
| Possible data sources | Retailer product data, published regional vintage-quality charts (e.g. from critics/trade bodies). |
| Current availability | Structured but inconsistent. ÁTVR provides a real structured field (`ProductYear`); Sante and Uva derive it via regex/heuristics over free text (title/tags), including a fallback that accepts "any tag that parses as an int within 30 years of current year" (`scrape_sante_wines.py:160-172`, per `scoring-data-readiness.md` row "Vintage"). |
| Structured / unstructured | Structured for ÁTVR; heuristically derived from unstructured text for Sante/Uva. |
| Deterministic / AI-assisted | ÁTVR: deterministic passthrough. Sante/Uva: deterministic regex, but heuristic/fragile — effectively unverified extraction, not a true source field. |
| Reliability | Medium — high for ÁTVR, lower and unverified for Sante/Uva; no non-vintage (NV) flag exists beyond an inconsistent "0" default. |
| Refresh frequency | Static once bottled; the catalog itself refreshes daily as new vintages replace old ones. |
| Cost to obtain | Low (already captured); a confidence flag on the heuristic-derived rows is a cheap addition. |
| Legal / licensing | None. |
| Explainability | High. |
| Confidence impact | High — vintage reliability should directly gate how much weight critic scores/vintage charts get, since both are vintage-specific. |
| Should influence | Quality (combined with regional vintage charts) and Confidence (extraction-method reliability). |
| Notes | A vintage-confidence flag is recommended regardless of scoring design, given the heuristic extraction risk already flagged in `scoring-data-readiness.md`. |

### Grape varieties

| Attribute | Detail |
|---|---|
| What it measures | The grape(s) used. |
| Why it matters | Establishes stylistic expectations (typicity) and lets scoring/UX compare wines within the same varietal category rather than across incomparable styles. |
| Possible data sources | Retailer attributes/tags, technical sheets, label text. |
| Current availability | Free-text / structured but inconsistent. Present across all 3 sources with different extraction methods (ÁTVR attribute, Sante taxonomy-matched, Uva attribute/tag); comma-joined multi-grape strings with inconsistent separators and no cardinality info (`scoring-data-readiness.md` row "Grapes"). |
| Structured / unstructured | Structured field, unstructured content (free-text list). |
| Deterministic / AI-assisted | Deterministic extraction; would need a normalized grape/wine junction table to become truly structured. |
| Reliability | Medium — presence is reliable, completeness/ordering is not guaranteed. |
| Refresh frequency | Static. |
| Cost to obtain | Low-medium — mostly a normalization task on already-captured data. |
| Legal / licensing | None. |
| Explainability | High. |
| Confidence impact | Low to Medium alone; more valuable combined with Blend percentages. |
| Should influence | Quality (weak, mostly via style/typicity context) and Confidence (as corroborating detail). |
| Notes | Best used as context for interpreting other signals (e.g., critic scores, style) rather than a direct quality driver by itself. |

### Blend percentages

| Attribute | Detail |
|---|---|
| What it measures | The proportion of each grape in a blend. |
| Why it matters | Refines the Grape varieties signal — "60% Cabernet Sauvignon, 40% Merlot" is meaningfully different from an unweighted list, and matters for style/quality expectations in blend-driven regions (e.g. Bordeaux, Rioja). |
| Possible data sources | Technical sheets, producer websites, back labels — rarely in retailer catalog attributes. |
| Current availability | Absent — no blend-percentage data anywhere in the schema (`scoring-data-readiness.md` row "Grapes," gap note). |
| Structured / unstructured | Would arrive unstructured (technical sheets, label text) requiring extraction. |
| Deterministic / AI-assisted | AI-assisted extraction from text if pursued. |
| Reliability | Low today (absent); Medium if sourced from official technical sheets. |
| Refresh frequency | Static per vintage. |
| Cost to obtain | Medium-high — requires a new source (technical sheets aren't currently scraped from anywhere). |
| Legal / licensing | Low — factual composition data, though technical-sheet PDFs may carry producer copyright on the document itself (not the facts). |
| Explainability | High when present. |
| Confidence impact | Medium — refines confidence in style-based comparisons. |
| Should influence | Confidence primarily (refines Grape varieties); not a direct Quality driver on its own. |
| Notes | Low priority relative to bigger gaps (critic scores, appellation); revisit if technical sheets become a source. |

### Wine style (still/sparkling/fortified, sweetness, body)

| Attribute | Detail |
|---|---|
| What it measures | Structural/stylistic classification — category (still/sparkling/fortified), sweetness, body. |
| Why it matters | Describes *what kind* of wine it is, which is essential for filtering/UX and for comparing wines within a like-for-like cohort — but style is not itself a quality axis. |
| Possible data sources | Retailer category fields, proprietary taste-group codes, technical sheets. |
| Current availability | Structured but inconsistent, and ÁTVR-only in practice. `category` is mapped per-source, but `sweetness`/`boldness` are only decoded for ÁTVR wines (from proprietary `taste_group` codes); Sante and Uva always get `'N/F'`, so these fields are blank for every non-ÁTVR wine (`scoring-data-readiness.md` row "Wine style"). |
| Structured / unstructured | Structured for ÁTVR only. |
| Deterministic / AI-assisted | Deterministic lookup (ÁTVR codes); would need an independent classifier for Sante/Uva coverage. |
| Reliability | Medium — reliable for ÁTVR, absent (not merely low-quality) for the other two sources. |
| Refresh frequency | Static. |
| Cost to obtain | Medium — closing the Sante/Uva gap needs either a new classifier or manual/text extraction. |
| Legal / licensing | None. |
| Explainability | High. |
| Confidence impact | Low directly, but a missing style value should reduce confidence in any style-dependent comparison (e.g. comparing a sweet wine's rating against a dry-wine-only benchmark). |
| Should influence | **None for Quality** — style is a preference/categorization axis, not a quality axis (a sweet wine isn't better or worse than a dry one). Useful for Confidence (cohort comparability) and UX filtering. |
| Notes | Explicitly called out in the misleading-signals section: never let style attributes leak into a quality score, only into cohort selection for fair comparison. |

### Alcohol % (ABV)

| Attribute | Detail |
|---|---|
| What it measures | Alcohol by volume. |
| Why it matters | Mostly a style/balance descriptor; extreme values (very high or very low for the style) can *sometimes* correlate with balance issues, but ABV alone is a poor standalone quality proxy. |
| Possible data sources | Retailer product data, label/technical sheets. |
| Current availability | Structured, but partial. ÁTVR carries a genuine `abv` field (`ProductAlchoholVolume`, e.g. `scrape_red_wines.py:89`); Sante and Uva hardcode `0 as abv` in the intermediate model (`stg_all_wines.sql:262,296`) — i.e. not actually populated for those two sources. |
| Structured / unstructured | Structured for ÁTVR; absent (not merely unstructured) for Sante/Uva. |
| Deterministic / AI-assisted | Deterministic passthrough where present. |
| Reliability | Medium — reliable for ÁTVR only; the `0` default for Sante/Uva is a placeholder, not a real "0% ABV" fact, and must not be treated as data. |
| Refresh frequency | Static. |
| Cost to obtain | Low for ÁTVR (already present); would need new extraction for Sante/Uva. |
| Legal / licensing | None. |
| Explainability | Medium — meaningful to informed users, less so to casual buyers. |
| Confidence impact | Low. |
| Should influence | **None directly for Quality.** At most a Confidence/plausibility check (e.g. flag implausible values) or a style-cohort filter. |
| Notes | The Sante/Uva `0 as abv` default is a placeholder artifact, not a signal — any scoring logic must exclude it explicitly, not treat "0" as a real data point (same class of bug as the `is_organic` hardcoding below). |

---

## C. Certification & recognition

### Organic / biodynamic certification

| Attribute | Detail |
|---|---|
| What it measures | Whether the wine holds an organic or biodynamic production certification. |
| Why it matters | A production-method fact, not a taste/quality fact — there is no established evidence that organic/biodynamic certification correlates with sensory quality. It is a legitimate **value/positioning** signal (some buyers pay a premium for it) but a poor quality signal. |
| Possible data sources | Retailer flags, certification body registries (EU organic logo, Demeter for biodynamic). |
| Current availability | Structured but narrow, and currently **actively wrong** for two of three sources. `is_organic` is a genuine ÁTVR field (`ProductOrganic`), but Sante and Uva hardcode the value `'true'` for every single row (`stg_all_wines.sql:284,319`) — this is not scraped data, it's a constant. This constant currently feeds a real +10% multiplier in the live `recommendation` formula (`wines.sql:58-61`) for every Sante/Uva wine regardless of the truth (`scoring-data-readiness.md` row "Organic / production designation"). |
| Structured / unstructured | Structured field, but 2/3 of its current values are fabricated placeholders. |
| Deterministic / AI-assisted | Deterministic lookup where genuinely sourced. |
| Reliability | **Low as currently populated** — only the ÁTVR value is real; treat Sante/Uva values as unknown, not `true`, until fixed. |
| Refresh frequency | Static (certification renews annually but rarely lapses for an existing listing). |
| Cost to obtain | Low to fix at the source (remove the hardcoded constants) but requires confirming whether Sante/Uva actually expose this data at all. |
| Legal / licensing | None — public certification status. |
| Explainability | High. |
| Confidence impact | Should reduce confidence in the *organic claim itself* for non-ÁTVR wines until fixed, not boost anything. |
| Should influence | **Value at most, never Quality.** This is a live, current example of a misleading signal actively contaminating the existing score — see misleading-signals section. |
| Notes | This is not a hypothetical risk — it is happening today in production. Any new scoring design must either fix the Sante/Uva hardcoding or explicitly exclude this field until it does. |

### Awards

| Attribute | Detail |
|---|---|
| What it measures | Formal recognition from wine competitions (e.g. Decanter, IWSC, Concours Mondial). |
| Why it matters | Can corroborate quality, but competition rigor and selectivity vary enormously — some competitions award medals to a large majority of entrants, making an unqualified "has an award" flag weak evidence on its own. |
| Possible data sources | Competition result databases/websites, retailer callouts, back-label text. |
| Current availability | Absent — no source scrapes competition medals/awards of any kind (`scoring-data-readiness.md` row "Awards"). |
| Structured / unstructured | Would need new structured extraction (competition + medal tier + year), likely from unstructured sources initially. |
| Deterministic / AI-assisted | AI-assisted extraction from text; deterministic once matched against a known competition/tier registry. |
| Reliability | Low to Medium — highly dependent on which competition; requires a competition-prestige weighting to be meaningful at all. |
| Refresh frequency | Annual (competitions run yearly cycles). |
| Cost to obtain | High — requires an entirely new external source and a competition-credibility reference table. |
| Legal / licensing | Medium — competition result databases may restrict redistribution/scraping; check each source's terms before acquiring. |
| Explainability | High superficially ("won gold at X") but misleading if the competition's rigor isn't also shown. |
| Confidence impact | Low unless the competition is weighted by prestige — an unweighted award count can *lower* trust in the model if users learn some competitions are pay-to-play. |
| Should influence | Quality only if competition-prestige-weighted; otherwise risks being a misleading signal (see below). |
| Notes | Do not treat "has an award" as binary evidence — a competition-credibility reference table is a prerequisite, not an afterthought. |

### Competition medals

| Attribute | Detail |
|---|---|
| What it measures | The specific medal tier (gold/silver/bronze) within an award. |
| Why it matters | Same mechanism as Awards, one level more granular — but inherits the same "which competition" caveat. |
| Possible data sources | Same as Awards. |
| Current availability | Absent — same gap as Awards. |
| Structured / unstructured | Same as Awards. |
| Deterministic / AI-assisted | Same as Awards. |
| Reliability | Low to Medium, same caveat as Awards — a bronze at a rigorous competition can be more meaningful than gold at a lenient one. |
| Refresh frequency | Annual. |
| Cost to obtain | High — bundled with Awards acquisition. |
| Legal / licensing | Medium — same as Awards. |
| Explainability | High superficially, same misleading risk as Awards without prestige context. |
| Confidence impact | Low standalone. |
| Should influence | Quality only alongside a competition-prestige weighting; treat as an extension of Awards, not a separate signal to acquire independently. |
| Notes | Model this as a sub-attribute of Awards (competition + tier), not a standalone signal, to avoid double-counting. |

### Professional critic scores

| Attribute | Detail |
|---|---|
| What it measures | A named critic or publication's numeric/verbal quality assessment (e.g. Wine Spectator, Robert Parker/Wine Advocate, Jancis Robinson, James Suckling, Decanter). |
| Why it matters | This is the closest thing the wine industry has to an expert, trained, repeated-methodology quality assessment — critics score against a consistent internal rubric across thousands of wines, which crowd ratings and awards don't reliably do. It is the single most-cited gap in the current pipeline. |
| Possible data sources | Critic/publication websites and APIs (many are subscription/paywalled), aggregator sites, retailer callouts of critic scores. |
| Current availability | **Absent entirely** — only Vivino's crowd-sourced rating exists; no professional critic score of any kind is scraped anywhere in the pipeline. Explicitly flagged as the core gap in `scoring-data-readiness.md`: *"no professional critic score of any kind exists anywhere in the pipeline."* |
| Structured / unstructured | Would be structured if sourced from a critic API/database; unstructured if scraped from retailer free-text mentions. |
| Deterministic / AI-assisted | Deterministic if sourced structurally; AI-assisted extraction if pulled from free text. |
| Reliability | High — critics apply a consistent, disclosed methodology, and their track record is itself verifiable over time. |
| Refresh frequency | Per-vintage, updated as critics publish new tastings (often annually per region/release). |
| Cost to obtain | High — most reputable critic sources are subscription-gated or restrict redistribution; may require a licensing agreement rather than scraping. |
| Legal / licensing | **High** — critic scores are commercial IP; redistributing them (e.g. via the public website JSON export) without a license is a real legal exposure, distinct from scraping retailer catalog data. |
| Explainability | High — a named, credible source is maximally explainable to users ("rated 92 by Wine Spectator"). |
| Confidence impact | High — presence of one or more independent critic scores should substantially raise confidence in a quality estimate. |
| Should influence | Quality and Confidence — the strongest quality signal on this list, if it can be legally obtained. |
| Notes | Legal/licensing terms must be resolved *before* any acquisition work — this is the one signal on this list where the licensing question could block the whole approach, not just add cost. |

---

## D. Crowd & behavioral signals

### Crowd ratings (e.g. Vivino)

| Attribute | Detail |
|---|---|
| What it measures | Aggregate rating from a large pool of self-reported consumer reviews. |
| Why it matters | Large-sample crowd sentiment is genuinely informative, but it is a *different* thing than expert quality assessment — it reflects popularity, accessibility, and price-expectation bias as much as intrinsic quality (e.g. easy-drinking, inexpensive wines often over-index vs. structured, age-worthy wines that reward expertise). |
| Possible data sources | Vivino, CellarTracker, retailer review sections. |
| Current availability | Structured and reliable as a raw value, but architecturally overloaded today. `wine_ratings_vivino.rating` is fuzzy-matched per listing (`scrape_vivino_ratings.py`) and is the sole quality input to the current `recommendation` formula, raised to `rating^3.8` — a steep exponential that turns small rating differences into very large score swings (`vivino-dependency-map.md`, `wines.sql:51`). |
| Structured / unstructured | Structured. |
| Deterministic / AI-assisted | The rating itself is deterministic (an aggregate the source computes); the *match* between a listing and the right Vivino page is fuzzy/AI-assisted matching with no enforced confidence threshold before insert (`scrape_vivino_ratings.py:112-152`). |
| Reliability | Medium — the number itself is reliable once matched, but the matching step can silently attach the wrong wine's rating, and the current pipeline has no confidence gate on that match. |
| Refresh frequency | Continuous in principle (new reviews arrive daily); in this pipeline, gated by a 15-wines-per-run scrape limit (`scrape_vivino_ratings.py:211`). |
| Cost to obtain | Low (already built), but fragile — no committed DDL, no dbt tests, no source-freshness checks (`technical-debt-register.md` TD-04, TD-10). |
| Legal / licensing | Medium — scraping and redistributing a third party's crowd rating (verbatim, to a public website) carries ToS exposure distinct from using it internally only. |
| Explainability | High, but currently overstated by the `^3.8` transform, which isn't itself explainable to a user seeing the raw 0–5 star number. |
| Confidence impact | Should scale with review count (see Number of reviews, below) — currently entangled into the same formula rather than modeled as a separate confidence axis. |
| Should influence | Quality and Confidence — but the *volume* of reviews, not just the rating, should be the confidence lever (see next row). |
| Notes | Any independent scoring model must explicitly decide whether to keep, replace, or supplement this term — it is currently load-bearing for the entire visible catalog (Vivino match is an inner join; unmatched wines never appear on the site at all). |

### Number of reviews (review count)

| Attribute | Detail |
|---|---|
| What it measures | Sample size behind a crowd rating. |
| Why it matters | This is a textbook **confidence** signal, not a quality signal — a 4.5 rating from 5 reviews and a 4.5 rating from 5,000 reviews should never be scored as equally trustworthy, but they currently are treated as different *quality* multipliers rather than different *confidence* levels. |
| Possible data sources | Same as whichever crowd-rating source is used (Vivino today). |
| Current availability | Structured and reliable — `rating_count` is captured alongside `rating`, but is currently used as a **quality** multiplier (`rating_count_index`, a 0.8/0.9/0.95/1.0 tiered penalty below 100 reviews, `wines.sql:52-57`), not as an explicit confidence/error-bar concept (`vivino-dependency-map.md`). |
| Structured / unstructured | Structured. |
| Deterministic / AI-assisted | Deterministic. |
| Reliability | High as a raw count; the current *use* of it is the issue, not the data itself. |
| Refresh frequency | Continuous, gated by the same 15-per-run scrape limit as the rating itself. |
| Cost to obtain | Low — already captured. |
| Legal / licensing | Same as Crowd ratings (same source). |
| Explainability | High as a standalone fact ("based on 1,200 reviews"), which is more honest to a user than folding it invisibly into a single opaque score. |
| Confidence impact | This *is* the confidence signal for crowd ratings — arguably the clearest confidence signal on this entire list. |
| Should influence | **Confidence, not Quality.** This is the flagship example in the "should influence confidence instead of quality" section below. |
| Notes | The existing `rating_count_index` tiered penalty is exactly the anti-pattern this document recommends against: it treats "we don't have much data" as if it were "the wine is worse," rather than "we're less sure." Recommend decomposing this explicitly in any new design. |

### User behaviour (future: views, clicks, add-to-cart, repeat purchase on Godvinkaup)

| Attribute | Detail |
|---|---|
| What it measures | How Godvinkaup's own users interact with a listing. |
| Why it matters | First-party behavioral data is a potentially valuable *demand/value* signal (what sells, what gets revisited), but popularity is not quality — front-page placement, price, and marketing all drive clicks independently of how good a wine actually is, and a naive feedback loop (popular wines get shown more, so they get clicked more) can entrench arbitrary early rankings. |
| Possible data sources | Godvinkaup's own site/app analytics (does not exist yet — no product surface currently captures this). |
| Current availability | Absent — no website analytics or user-interaction capture exists in this repository's scope; the current website is a static JSON export with no feedback loop back into the ETL. |
| Structured / unstructured | Would be structured (event logs) if instrumented. |
| Deterministic / AI-assisted | Deterministic aggregation once instrumented. |
| Reliability | Unknown until built; inherently biased by whatever the current ranking/UI already surfaces (selection bias / feedback loop risk). |
| Refresh frequency | Continuous, if instrumented. |
| Cost to obtain | Medium — requires new product instrumentation (analytics events), not just an ETL change. |
| Legal / licensing | Medium — first-party user behavior data raises privacy/analytics-consent considerations (cookie/analytics disclosure), even though it's first-party. |
| Explainability | Low to a user ("popular with other buyers" is explainable; "ranked by click-through rate" is not something to expose directly). |
| Confidence impact | Low as a quality confidence signal; more relevant to a *value/demand* estimate. |
| Should influence | Value at most (popularity/demand), and only with explicit feedback-loop safeguards; should not influence Quality. |
| Notes | Flagged as a future signal specifically because of feedback-loop risk — recommend never wiring this directly into Quality even once available, and treating it as a separate "popularity" surface rather than blending it into the trust score. |

### Godvinkaup user ratings (future: native ratings/reviews)

| Attribute | Detail |
|---|---|
| What it measures | Direct, first-party quality ratings from Godvinkaup's own users, if a rating feature is built. |
| Why it matters | This would be the most promising future independent crowd-quality signal — first-party, not subject to third-party ToS/licensing risk, and directly relevant to Godvinkaup's actual user base (which may have different tastes/price sensitivity than Vivino's global population). |
| Possible data sources | A native ratings/reviews feature (does not exist yet). |
| Current availability | Absent — no product surface for user ratings exists yet; this is a roadmap item, not a current gap in the ETL. |
| Structured / unstructured | Would be structured (numeric rating + optional text) if built. |
| Deterministic / AI-assisted | Deterministic aggregation; AI-assisted if free-text reviews are also mined for structured tasting notes. |
| Reliability | Unknown until built and until sample sizes are large enough — early on, this would suffer the same low-review-count problem as Vivino does today, likely worse (smaller user base). |
| Refresh frequency | Continuous, once built. |
| Cost to obtain | High — this is a product feature, not a scraper; requires UX, moderation (spam/fake review risk), and a meaningful user base before it's useful. |
| Legal / licensing | Low — first-party data Godvinkaup fully owns, no third-party redistribution risk. |
| Explainability | High — "rated by Godvinkaup users" is maximally legible and legally clean to show. |
| Confidence impact | Should be explicitly review-count-gated from day one, learning directly from the Number-of-reviews lesson above — do not repeat the same conflation of sample size with quality. |
| Should influence | Quality and Confidence, once volume is sufficient — but should launch with confidence-gating built in, not retrofitted. |
| Notes | Strategically important: this is the one signal on the list that, if built, gives Godvinkaup a rating source it fully owns and controls, unlike every other signal in this document. Worth prioritizing on the product roadmap even though it's currently a blank slate. |

---

## E. Descriptive & unstructured content

### Retail descriptions

| Attribute | Detail |
|---|---|
| What it measures | Marketing copy written by the retailer/producer for a listing. |
| Why it matters | A rich source to *mine* for other structured signals (grapes, food pairings, awards mentions, tasting notes) — but as marketing copy, it is not itself objective evidence of quality and should never be scored directly. |
| Possible data sources | Retailer product pages. |
| Current availability | Free-text only, uneven coverage. ÁTVR descriptions are scraped and upserted (`landing.atvr_wine_descriptions`) but only backfilled for wines missing one, so coverage/freshness is uneven; Sante strips `body_html` into plain text; **Uva has no description at all** — hardcoded to `'N/A'` (`stg_all_wines.sql:323`, per `scoring-data-readiness.md` row "Retailer description"). |
| Structured / unstructured | Unstructured. |
| Deterministic / AI-assisted | Would need NLP/AI-assisted extraction to pull structured facts (grape %, awards, tasting notes) out of this text. |
| Reliability | Low as a direct quality signal (it's marketing copy); Medium as a source to mine for *other* structured facts, with per-source coverage gaps. |
| Refresh frequency | Static per listing; ÁTVR's backfill-only refresh means some descriptions may be stale relative to the current listing. |
| Cost to obtain | Low to capture (already scraped for 2/3 sources); medium to extract structured facts from it. |
| Legal / licensing | Low — retailer's own marketing copy, though verbatim republishing (e.g. to Godvinkaup's website) should still respect the retailer's copyright on the text itself. |
| Explainability | Medium — fine to show verbatim to users, but not to cite as "evidence" behind a quality score. |
| Confidence impact | None directly; a source for improving other signals' confidence via corroboration (e.g. confirming a grape variety already extracted elsewhere). |
| Should influence | **None directly.** Should only feed the pipeline as raw material for extracting other, separately-assessed signals. |
| Notes | Classic misleading-signal risk: marketing copy can *sound* like quality evidence ("exceptional," "award-winning") without being verifiable — treat superlatives in retail copy as noise, not signal, unless independently corroborated (e.g. against the Awards signal). |

### Technical sheets

| Attribute | Detail |
|---|---|
| What it measures | Producer-published analytical data — residual sugar, acidity, pH, aging vessel/duration, production volume, official blend %. |
| Why it matters | Objective, lab-verified facts about the wine, as opposed to marketing copy — a meaningfully more trustworthy unstructured source than retail descriptions, when available. |
| Possible data sources | Producer/importer websites, often as downloadable PDFs. |
| Current availability | Absent — not scraped from any of the 4 current sources. |
| Structured / unstructured | Semi-structured in the source (often tabular within a PDF/webpage) but would require new extraction work to become usable. |
| Deterministic / AI-assisted | AI-assisted extraction (PDF/HTML table parsing) to structure it; deterministic once parsed. |
| Reliability | High — this is closer to ground truth than any other unstructured source on this list, since it's the producer's own lab/production data. |
| Refresh frequency | Static per vintage. |
| Cost to obtain | Medium-high — requires a new source per producer, with no consistent format across producers. |
| Legal / licensing | Low — factual data, though the sheet document itself may be producer copyright; extract facts, don't republish the sheet verbatim. |
| Explainability | High. |
| Confidence impact | High when present — genuinely corroborating, objective evidence. |
| Should influence | Quality (composition/style facts) and Confidence (corroboration). |
| Notes | Worth prioritizing above Awards/Retail descriptions if pursuing new unstructured sources, given its higher inherent reliability. |

### Food pairings

| Attribute | Detail |
|---|---|
| What it measures | Recommended dishes/cuisines to pair with the wine. |
| Why it matters | A UX/utility feature for buyers, not a quality signal — pairing suitability is orthogonal to how good the wine is. |
| Possible data sources | Retailer attributes/tags, a food-pairing translation table. |
| Current availability | Structured for ÁTVR (`ProductFoodCategories`) and Uva (attribute `[9]`); absent for Sante (`'N/F'`). Mapped through `wine_food_pairings.sql`, which joins against `landing.wine_food_translations` — a source declared in dbt but with **no script or seed anywhere in this repo that populates it** (unresolved question in `current-etl-architecture.md §11.1`). |
| Structured / unstructured | Structured (coded categories), but the translation table's provenance is unverified. |
| Deterministic / AI-assisted | Deterministic lookup, contingent on the unverified translation table actually being populated and current. |
| Reliability | Medium — structurally sound where present, but Sante has zero coverage and the translation table's freshness/ownership is an open question. |
| Refresh frequency | Static. |
| Cost to obtain | Low — already captured for 2/3 sources; resolving the translation-table provenance is the main open task. |
| Legal / licensing | None. |
| Explainability | High, but purely descriptive. |
| Confidence impact | None. |
| Should influence | **None.** Pure product/UX metadata. |
| Notes | Resolve the `wine_food_translations` provenance question before relying on this for anything beyond display, regardless of scoring design. |

### Ageability

| Attribute | Detail |
|---|---|
| What it measures | How well a wine is expected to improve/hold up with cellaring, and over what time window. |
| Why it matters | Relevant to quality assessment for buyers who cellar wine, and often correlates with structural factors (tannin, acidity, appellation/classification) that critics already factor into their scores — but is a genuinely distinct axis from "quality right now." |
| Possible data sources | Critic notes (often include a drinking window), technical sheets, appellation/classification norms. |
| Current availability | Absent — no field or derived estimate exists anywhere in the pipeline. |
| Structured / unstructured | Would arrive unstructured (critic notes, technical sheets) initially. |
| Deterministic / AI-assisted | AI-assisted extraction from critic/technical text; could later be modeled deterministically from structural proxies (appellation, grape, vintage) if no direct source is available. |
| Reliability | Low today (absent); Medium if sourced from critic drinking-window notes specifically. |
| Refresh frequency | Static per vintage. |
| Cost to obtain | Medium-high — realistically arrives as a byproduct of acquiring Professional critic scores or Technical sheets, not as a standalone acquisition. |
| Legal / licensing | Same as whichever source it's extracted from (critic notes: high; technical sheets: low). |
| Explainability | High — directly useful and interesting to communicate to buyers ("best from 2027–2035"). |
| Confidence impact | Low to Medium as a standalone signal. |
| Should influence | Quality, for buyers evaluating cellaring wines specifically — but this is a "quality for what purpose" question, worth flagging as a design decision (see notes) rather than folding silently into a single score. |
| Notes | Consider surfacing ageability as its own labeled dimension rather than blending it into a single quality number — "high quality but not built to age" and "will improve significantly with age" are both true and both useful, but conflating them loses information a buyer would want. |

---

## F. Commercial

### Bottle size

| Attribute | Detail |
|---|---|
| What it measures | Volume (375ml, 750ml, 1.5L, etc.). |
| Why it matters | Not a quality signal at all — but essential for computing price-per-ml, i.e. Value. |
| Possible data sources | Retailer product data. |
| Current availability | Structured but inconsistent, and currently causing silent data loss. `volume` exists across all 3 sources, but `wines.sql:108` filters to `volume in (0, 750)` only — any half-bottle, magnum, or other non-750ml size is **excluded from the mart entirely** today, not merely mis-scored (`scoring-data-readiness.md` row "Bottle size"). |
| Structured / unstructured | Structured for ÁTVR; parsed via regex with a 750ml default for Sante/Uva. |
| Deterministic / AI-assisted | Deterministic. |
| Reliability | Medium — reliable where a real value is captured; the Sante/Uva 750ml "default" is a placeholder for missing data, not a verified fact. |
| Refresh frequency | Static. |
| Cost to obtain | Low — already captured; fixing the exclusion filter is a bug fix, not new acquisition. |
| Legal / licensing | None. |
| Explainability | High. |
| Confidence impact | Low, mostly a normalization input. |
| Should influence | **Value only, never Quality.** |
| Notes | This existing 750ml filter is a real, current bug independent of any new scoring work — worth fixing regardless of what scoring model gets built, since it silently shrinks the catalog today. |

### Retail price

| Attribute | Detail |
|---|---|
| What it measures | Current listing price. |
| Why it matters | The denominator of Value — by definition, price should never be an input to Quality, or the system becomes circular (expensive wines scoring as "better" because they're expensive, rather than being *evaluated against* their price). |
| Possible data sources | Retailer product data. |
| Current availability | Structured and reliable — `price` is captured across all 3 sources, all in ISK, and already load-bearing in the existing `recommendation` formula's `volume / sqrt(price)` term (`scoring-data-readiness.md` row "Price", `wines.sql:64,72`). |
| Structured / unstructured | Structured. |
| Deterministic / AI-assisted | Deterministic. |
| Reliability | High. |
| Refresh frequency | Daily (re-scraped on every run) — genuinely volatile, unlike most other signals on this list. |
| Cost to obtain | Low — already captured. |
| Legal / licensing | None. |
| Explainability | High. |
| Confidence impact | None directly for quality confidence; relevant to value-estimate confidence (see Historical price). |
| Should influence | **Value only, never Quality.** This is the clearest, most important entry in the "never influence quality" section below — it's the one signal where getting this wrong (letting price leak into quality) actively defeats the purpose of an independent, trustworthy score. |
| Notes | Confirm currency handling remains ISK-only as sources are added; no currency field currently exists to guard against this changing silently. |

### Historical price

| Attribute | Detail |
|---|---|
| What it measures | How a wine's price has moved over time. |
| Why it matters | A single price snapshot can't tell you if today's price is a good deal — historical price tells you whether this listing is priced high, low, or normal relative to its own history, materially sharpening the Value estimate. |
| Possible data sources | Would require retaining price history over time — not a new external source, but a retention/snapshotting change to the existing pipeline. |
| Current availability | Absent structurally, not just unscraped. `landing.*` tables are `DROP TABLE ... CASCADE` and fully recreated every run, destroying the prior day's data with no retention (`technical-debt-register.md` TD-11); dbt's `snapshots/` directory is empty despite being declared in `dbt_project.yml`. |
| Structured / unstructured | Would be structured (a simple time series) once retained. |
| Deterministic / AI-assisted | Deterministic — purely a retention/schema change, no extraction or matching involved. |
| Reliability | Would be High once implemented — it's just retained instances of an already-reliable field. |
| Refresh frequency | Daily accumulation. |
| Cost to obtain | Low-medium — primarily an engineering task (dbt snapshots or an append-only price table), not new data acquisition. |
| Legal / licensing | None. |
| Explainability | High — "this is 15% below its typical price" is an intuitive, trustworthy thing to show a user. |
| Confidence impact | Improves confidence in the Value estimate specifically (more price history = more reliable "is this a good deal" judgment). |
| Should influence | Value, and Confidence in the value estimate. |
| Notes | This is a prerequisite-type gap: per `technical-debt-register.md` TD-11, this should be scoped as infrastructure work *before* any value-trend feature is designed, not discovered as a blocker mid-design. |

### Availability (in-stock / delisted)

| Attribute | Detail |
|---|---|
| What it measures | Whether a listing is currently sellable. |
| Why it matters | An operational/filtering fact, not a quality or value signal — but worth tracking explicitly since sellout speed *could* be a weak future demand proxy (with the same feedback-loop caution as User behaviour, above). |
| Possible data sources | Retailer catalogs (implicit: presence/absence in the daily scrape). |
| Current availability | Structured and reliable, but binary and history-free. `dim_wines`'s `valid` flag (1 = present in today's scrape, 0 = expired) tracks current presence (`dim_wines.sql:15-28`), but because `landing.*` tables are fully replaced daily with no retention, there's no history of *when* a wine went in or out of stock, or how often. |
| Structured / unstructured | Structured. |
| Deterministic / AI-assisted | Deterministic. |
| Reliability | High for current state; the underlying history needed for a sellout-speed proxy doesn't exist (same root cause as Historical price — TD-11). |
| Refresh frequency | Daily. |
| Cost to obtain | Low for current state (already exists); same retention work as Historical price would be needed for any trend-based use. |
| Legal / licensing | None. |
| Explainability | High as a simple in-stock flag; low if ever used as an implicit popularity proxy (not something to explain to a user as "evidence"). |
| Confidence impact | None directly. |
| Should influence | **None** for Quality/Value today; purely a display/filter fact. A future sellout-velocity signal, if built, should be treated with the same caution as User behaviour above. |
| Notes | Keep this simple and operational; resist the temptation to over-interpret stock turnover as a quality proxy without first ruling out confounds (price cuts, single-retailer allocation quirks, seasonal buying). |

### Importer

| Attribute | Detail |
|---|---|
| What it measures | The importer/distributor who brought the wine into the Icelandic market. |
| Why it matters | Importers curate portfolios, and a reputable importer's selection can be a weak-to-moderate quality prior (similar mechanism to Producer track record, one level removed) — some buyers explicitly trust specific importers' palates. |
| Possible data sources | Retailer product pages (often listed but not always structured), importer websites/portfolios. |
| Current availability | Absent — no importer/distributor field is scraped from any of the 3 retailers (`scoring-data-readiness.md` row "Importer"). |
| Structured / unstructured | Would likely be structured if present on retailer pages but simply isn't captured; unverified whether the underlying retailer pages even expose it. |
| Deterministic / AI-assisted | Deterministic extraction if the field exists on-page; would need confirmation it's actually available before scoping. |
| Reliability | Unknown until sourced. |
| Refresh frequency | Rarely changes for an existing listing. |
| Cost to obtain | Medium — would require new scraper fields/logic across sources; unclear if worth it until confirmed the retailer pages expose it. |
| Legal / licensing | Low — factual, publicly disclosed if present. |
| Explainability | Medium — meaningful to enthusiasts, less legible to casual buyers. |
| Confidence impact | Low to Medium — a weaker, more diffuse version of the Producer track-record effect. |
| Should influence | Quality (weak prior, analogous to Producer) and Confidence, if sourced. |
| Notes | Lower priority than Producer canonicalization or Appellation, given uncertain availability and a weaker mechanism; worth a quick scoping check (does the retailer page even show this?) before committing engineering time. |

---

## Cross-cutting synthesis

### Signals that should never influence quality

- **Retail price** — it's the denominator of Value; letting it influence Quality makes the system circular (expensive = "better" by construction) and defeats the entire point of an *independent* score.
- **Bottle size** — a packaging fact, relevant only to price-per-ml Value math.
- **Wine style (sweetness/body/category)** — a preference/categorization axis, not a quality axis; a sweet wine is not inherently worse than a dry one.
- **Alcohol %** — at most a plausibility check or style-cohort input; not a standalone quality proxy.
- **Retail descriptions** — marketing copy; a source to *mine* other signals from, never evidence in itself.
- **Food pairings** — pure UX/utility metadata, orthogonal to quality.
- **Availability (in-stock/delisted)** — an operational fact, not evidence about the wine itself.

### Signals that should influence confidence instead of quality

- **Number of reviews** — the flagship case. This is currently baked into the *quality* formula as `rating_count_index` (a 0.8–1.0 multiplier below 100 reviews). It should instead widen or narrow an explicit error bar around the quality estimate, never adjust the estimate itself.
- **Vintage extraction reliability** — whether a vintage was structurally sourced (ÁTVR) or heuristically regex-derived (Sante/Uva) should gate how much weight vintage-dependent signals (critic scores, vintage charts) get, not feed quality directly.
- **Producer canonicalization certainty** — how confidently a free-text producer string was matched to a canonical entity should scale how much the producer track-record prior contributes.
- **Blend percentages / technical sheet presence** — corroborating detail that sharpens confidence in the Grape varieties / Wine style signals, without being a quality driver on their own.

### Signals that should only influence value

- **Retail price** (definitionally — see above; the same signal appears in both lists because it's the anchor of Value and the paradigm case of "must not touch Quality").
- **Historical price** — sharpens whether current price is a good or bad deal, not whether the wine is good.
- **Bottle size** — price-per-ml normalization.
- **Organic/biodynamic certification** — a positioning/premium-pricing fact, not a taste-quality fact (see below).
- **User behaviour (future)** — a demand/popularity proxy, useful for value/merchandising, risky if blended into quality.

### Signals that appear useful but are actually misleading

- **Organic/biodynamic certification treated as quality** — this is not a hypothetical: it is happening in production today. Sante and Uva hardcode `is_organic = 'true'` for every row (not scraped, a constant), and that constant currently feeds a real +10% multiplier in the live `recommendation` formula. There is no evidence base that organic/biodynamic status correlates with sensory quality — it's a legitimate values/positioning signal, not a taste signal, and right now it's silently inflating scores for two-thirds of the catalog based on fabricated data.
- **Region/Country as a direct quality prior** — "it's from Bordeaux/France" is a stereotype, not evidence, when applied to an individual bottle; region only becomes meaningful combined with an actual regulatory tier (Appellation/Classification) or corroborating signals.
- **Awards/competition medals, unweighted** — some competitions award medals to a large majority of entrants; an unweighted "has a medal" flag can be actively misleading without a competition-prestige reference table, potentially making *less* rigorously judged wines look equally validated as genuinely competitive ones.
- **Crowd rating volume treated as a quality multiplier** (see previous section) — conflating "we have a lot of data" with "the wine is better" is a subtle but real distortion already present in the live formula.
- **Raw ABV values from Sante/Uva** — the current `0 as abv` default for these sources is a placeholder for missing data, not a real "0% alcohol" fact; treating it as data rather than a null would corrupt any ABV-based logic.

---

## Five signals most likely to make an independent score trustworthy

Ranked by combined reliability, explainability, and independence from the very Vivino dependency
this exercise is meant to reduce:

1. **Professional critic scores** — the single highest-value gap. Critics apply a consistent,
   disclosed methodology across large numbers of wines, giving both high reliability and high
   explainability. This is the one signal that would most directly deliver on "independent
   scoring," precisely because it doesn't depend on Vivino at all. Legal/licensing terms must be
   resolved first, but the payoff justifies prioritizing that resolution early.
2. **Crowd rating combined with an explicit, separated confidence weighting (review count)** —
   not "replace Vivino," but fix how it's used: separate the rating (quality input) from the
   review count (confidence input) instead of blending both into one exponential-and-tiered
   formula. This alone would make the *existing* signal meaningfully more trustworthy, and
   generalizes cleanly to native Godvinkaup ratings later.
3. **Canonical producer identity and track record** — turns a currently-fragmented, three-source
   free-text field into the strongest available prior for a wine with sparse direct evidence
   (new listings, low review counts). High leverage relative to cost, since the raw data already
   exists — the gap is entity resolution, not acquisition.
4. **Appellation / classification tier** — the most under-exploited structured-quality proxy
   available: legally encoded, not just reputational, and currently completely absent from the
   schema despite being frequently present in retailer text. Meaningfully stronger than raw
   region/country, and cheap relative to critic scores or awards (extraction from data already
   captured, not a new external source).
5. **Vintage, correctly extracted and cross-referenced against regional vintage-quality data** —
   vintage is nearly free (mostly already captured, needs a reliability flag for the heuristic
   Sante/Uva extraction) and, combined with published regional vintage charts, turns a currently
   inert field into a genuine, externally-verifiable quality input rather than just a filter/display
   attribute.

Notably, none of these five require inventing a new formula — they require, in order: resolving a
licensing question, decomposing an existing conflated formula, building an entity-resolution layer,
adding one new structured field, and adding one reliability flag. That's a deliberately
low-formula-risk starting set for the next design phase.
