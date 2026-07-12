# What Should Godvinkaup Become?

**Architecture & Product Design Memo — Godvinkaup**

> Not a Vivino replacement. A platform that turns a daily scrape into an owned, evidence-graded
> opinion about wine — one that gets more trustworthy every year instead of more dependent.

| | |
|---|---|
| **Scope** | Full-repo discovery, code-verified |
| **Horizon** | 5 years |
| **Status** | Design exercise, no code changed |
| **Prepared** | 2026-07-10 |

## Table of contents

1. [Vision](#01--vision)
2. [Guiding principles](#02--guiding-principles)
3. [Domain model](#03--domain-model)
4. [Where intelligence should live](#04--where-intelligence-should-live)
5. [Evidence, provenance & uncertainty](#05--evidence-provenance--uncertainty)
6. [What the scoring system should score](#06--what-the-scoring-system-should-score)
7. [Retailer matching](#07--retailer-matching)
8. [Target architecture](#08--target-architecture)
9. [Alternative architectures considered](#09--alternative-architectures-considered)
10. [Risks](#10--risks)
11. [Open questions](#11--open-questions)
12. [Roadmap](#12--roadmap)
13. [Keep vs. retire](#13--keep-vs-retire)

---

## 01 — Vision

### Stop replacing Vivino. Start owning an opinion.

The brief begins from "Vivino is no longer viable, what replaces it?" — that framing is worth
resisting. Swapping one external rating source for another (or for several) fixes an outage, not
the platform. It leaves Godvinkaup exactly what it is today: a nightly re-packager of someone
else's opinion about wine, with a UI and a price column attached.

Read literally, the current pipeline has no independent judgment anywhere in it. `marts.wines`
inner-joins Vínbúðin/Sante/Uva listings against Vivino ratings; if there is no Vivino row, the wine
does not exist on the site (`wines.sql:103-105`). The "recommendation" score is
`power(vivino.rating, 3.8)` times a volume/price term — a transformation of Vivino's number, not a
second opinion. Remove Vivino and there is nothing left to rank with.

Five years out, Godvinkaup should be the opposite of that: a platform that holds a **graded,
sourced, continuously-revised opinion** about every wine sold in Iceland — built from many weak
signals (crowd ratings, critic data where available, retailer copy, and increasingly its own users)
rather than one strong one. No single upstream source should be able to freeze the catalog or
invalidate the ranking by disappearing. That resilience is the actual point, not "which rating site
do we scrape instead."

The second, larger shift: Godvinkaup should stop being only a pipe from retailers to a static
export, and start being a place people *return to*. Every view, save, and click-through to a
retailer is a first-party signal Vivino will never give away and no replacement source will either.
A platform that captures even a modest stream of its own behavioral data starts, within a couple of
years, holding something no scraped competitor site has: a taste signal specific to what Icelandic
drinkers actually buy, not what a global crowd rates.

> **Reframed question.** Not "what replaces Vivino's rating column" but "what does Godvinkaup know
> about a wine that it didn't have to ask anyone else for, and how does that share grow every
> year." That's the north star the rest of this memo is designed around.

---

## 02 — Guiding principles

### Eight rules the architecture should never violate

**01. Evidence over assertion.**
No rating, match, or attribute is stored as a bare value. Every derived fact carries a source, a
method, a confidence, and a timestamp. If you can't say where a number came from, it isn't ready to
rank a wine.

**02. A duplicate is a bug; a false merge is an incident.**
Two rows for the same wine is a UX annoyance, fixable later. Two *different* wines collapsed into
one — one wrongly inheriting the other's rating, price history, or reviews — destroys trust the
moment a user notices. Every identity decision should be biased toward the cheaper mistake.

**03. Quality and value are different axes, always.**
Quality is a property of the liquid (does it taste good). Value is a property of a listing (is it
worth this price, at this retailer, today). They must never be collapsed into one blended number the
way `recommendation` is today — a wine's quality doesn't change when Sante runs a sale.

**04. Decide the grain before writing the formula.**
"One row" must mean one specific thing — a retailer listing, a vintage, a wine — before any score
touches it. The current schema scores at the listing grain by accident (`dim_wines.id` is a
retailer SKU), which is the single deepest defect in the system today.

**05. History is a feature, not exhaust.**
Price trends, rating drift, and "this listing used to be linked to a different wine" are all
product features waiting on data that today is destroyed daily (`DROP TABLE ... CASCADE` every
scrape run). Nothing that could plausibly become a trend line should overwrite itself in place.

**06. Deterministic first, AI where determinism fails, a human where AI is unsure.**
Cheap, explainable techniques (barcode match, trigram similarity, exact producer+vintage+volume)
should resolve the easy majority. AI earns its place only on the residual hard cases, and never as
the sole, silent authority on identity.

**07. Own the signal.**
Every architecture decision should ask "does this make Godvinkaup less dependent on an external
source next year, or more." First-party interaction data compounds; borrowed ratings don't.

**08. Simplicity survives.**
The existing codebase already states this well — correctness, readability, maintainability,
performance, in that order. A five-year platform is built by a small team (today, effectively one
person); every entity and layer added below has to earn its complexity.

---

## 03 — Domain model

### Four nouns fix most of the register

Technical-debt item TD-16 names the real problem precisely: there is no distinction between a wine,
a vintage, a retailer's listing of it, and a bottle size. Today's `dim_wines`/`wines` tables key on
the retailer's own SKU id, so the "same wine" at two retailers, or two vintages of one wine at the
same retailer, are unrelated rows that each independently win or lose their own Vivino coin-flip.
Nearly every downstream distortion — the catalog cap, the fake organic bonus, the impossibility of a
clean quality score — traces back to this single modeling gap.

**Fig. 1 — core entities and where each score attaches**

```text
 PRODUCER (canonical)        REGION (country → area → appellation)
        │                              │
        └───────────────┬──────────────┘
                         ▼
                 ┌───────────────┐
                 │     WINE      │   producer + label + style
                 │  optional,    │   "Château X Réserve" — may not
                 │  confidence-  │   exist yet for the long tail
                 │  scored       │
                 └───────┬───────┘
                         │ 1
                         ▼ N
                 ┌───────────────┐
                 │    VINTAGE    │   wine + year (or NV)
                 │ ── QUALITY ── │ ◂── Quality Score lives here
                 │  SCORE HERE   │      (source-weighted, confidence-graded)
                 └───────┬───────┘
                         │ 1
                         ▼ N
                 ┌───────────────┐        N:1        ┌───────────────┐
                 │     MATCH     │───────────────────▸│    LISTING    │
                 │  (evidence)   │◂───────────────────│  retailer SKU │
                 │ confidence,   │                     │ price, stock, │
                 │ method, time, │                     │ bottle size   │
                 │ reviewer      │                     │ ── VALUE ──   │ ◂── Value Score
                 └───────────────┘                     │  SCORE HERE   │      lives here
                                                        └───────┬───────┘
                                                                │ N:1
                                                                ▼
                                                        ┌───────────────┐
                                                        │   RETAILER    │
                                                        │  ÁTVR / Sante │
                                                        │  / Uva / ...  │
                                                        └───────────────┘
```

Two entities do the real work here. **Vintage** is where a Quality Score belongs, because quality
genuinely varies by year — a 2018 and a 2021 of the same wine are not interchangeable, and today's
schema has no way to say that. **Listing** is where a Value Score belongs, because value is
inseparable from a specific price at a specific retailer on a specific day — the same Vintage can
be a steal at Sante and overpriced at ÁTVR simultaneously. Conflating these two grains into one
`recommendation` column, as today's formula does, is the single biggest reason the current score
can't be trusted or explained.

**Match** is promoted from an implicit join condition to a first-class, auditable row. Today, "is
this ÁTVR listing the same wine as this Vivino page" is decided once, silently, inside a Python
script, and the only trace left is two numeric columns (`name_score`, `producer_score`) that
nothing downstream reads — `verified` is written as `NULL` on every single row
(`scrape_vivino_ratings.py:192`), so the confidence work the matcher already does is thrown away.
Making Match a real, versioned entity is what lets "canonical wines are optional and
confidence-driven" — the brief's own stated requirement — actually be enforced in the schema rather
than asserted in a design doc.

### Immutable, historical, versioned — not the same thing

*Handling policy by entity — verified against current behavior where a comparison exists*

| Entity | Policy | Why | Current behavior |
|---|---|---|---|
| Wine / Vintage identity | Near-immutable once created | A 2019 Château X doesn't stop being a 2019 Château X | Doesn't exist as an entity today |
| Wine / Vintage attributes | Versioned, corrections keep prior value + reason | Grape mix or region can be corrected without erasing what was believed before | Overwritten silently (`dbt run` rebuilds the table each time) |
| Listing (price, stock) | SCD2 history (dbt snapshot) | Price trend is a product feature; "in stock since" matters | `DROP TABLE ... CASCADE` every run — zero history (TD-11) |
| Match (evidence) | Append-only, superseded not deleted | Need to answer "why did this listing show this wine 3 months ago" | Upserted in place (`ON CONFLICT ... DO UPDATE`), history destroyed on every re-scrape |
| Rating / evidence ledger | Strictly append-only | A rating trend over time is signal; overwriting it erases the only time-series data the platform could ever have | Overwritten in place (`modified_date = excluded...`) — this is actively destroying history today |
| Quality / Value Score | Recomputed + versioned by model version | Reproducibility: same inputs + model version ⇒ same output, always | Deterministic formula, but untested, unversioned, and silently changes meaning if the Vivino scale shifts |

---

## 04 — Where intelligence should live

### Match the tool to the epistemic weight of the decision

The existing split — Airflow orchestrates, dbt transforms, business logic stays out of Python where
practical — is already the right shape (this is written into `AGENTS.md` and it's sound engineering
practice independent of who wrote it). The gap isn't tooling, it's that every layer is currently
used for exactly one purpose (scrape, union, join, export) and none of them carry any notion of
confidence.

*Capability → layer, with the reasoning that justifies it*

| Capability | Layer | Confidence class |
|---|---|---|
| Scheduling, retries, cross-DAG dependency, alerting | Airflow | Deterministic |
| Unit/currency normalization, filtering, aggregation, the Quality/Value formulas themselves | dbt / SQL | Deterministic |
| Candidate generation for matching (trigram similarity, phonetic normalization, blocking on producer+vintage+volume) | Python / SQL | Deterministic, explainable |
| Final match confidence scoring | Python model → written as evidence | AI-assisted, always scored |
| Free-text producer/region canonicalization where rules fail | LLM, gated by confidence | AI-assisted |
| Structured extraction from retailer descriptions (tasting notes, grape %, style) where no structured field exists | LLM, tagged "machine-extracted" | AI-assisted |
| Semantic search / discovery text, "find me something like this" | Embeddings (already in place via Qdrant — keep) | AI-assisted |
| Merging two catalog identities into one canonical Wine at borderline confidence | Human review queue | Human-gated, never automatic |
| Price, ABV, volume, availability, legal/compliance fields | Retailer feed, verbatim | Never AI |

The rule of thumb worth stating plainly: **an LLM is a candidate generator and an explainer, never
a merge authority.** Given the brief's own framing — false positives are worse than duplicates —
the system should never let a model's fluency substitute for an explicit, auditable confidence
number. A hallucinated "yes, same wine" stated persuasively is more dangerous than a fuzzy-match
score of 0.6 that visibly says "uncertain."

---

## 05 — Evidence, provenance & uncertainty

### An evidence ledger, not a bridge table

`marts.wine_ratings_vivino` is architecturally a bridge table today, but it behaves like a cache:
every re-scrape overwrites `rating`/`rating_count` in place, and the `verified` column — clearly
intended to hold exactly the kind of confidence flag this memo is arguing for — has been writing
`NULL` on every single insert since the code was written (TD-18). The infrastructure for provenance
already exists in the schema; it's simply never populated or read.

The fix is a pattern change, not a bigger table: every fact that could be wrong gets a row in an
**append-only evidence ledger**, not a column that gets silently overwritten. A rating from Vivino,
a rating from a future second source, and Godvinkaup's own eventual user ratings are all the same
shape of fact — `(subject, source, value, scale, sample_size, confidence, retrieved_at)` — and none
of them should ever `UPDATE` a prior row. The Quality Score becomes a query over that ledger
(weighted by source reliability and recency) instead of a hardcoded reference to one vendor's
column.

**Fig. 2 — how a confidence-tagged fact should look, end to end**

```text
  source: vivino          confidence: high    (crowd, n=1,240, matched 0.91)
  source: sante_desc_llm  confidence: medium  (extracted, unreviewed)
  source: atvr_organic    confidence: low     (hardcoded 'true' for all Sante/Uva rows today — TD readiness doc)
                                    │
                                    ▼
                   Quality Score = weighted(evidence, by source reliability × confidence × recency)
                   shown with its own confidence band, not just a single number
```

This directly resolves the Sante/Uva `is_organic` bug flagged in the readiness doc: both sources
currently hardcode `'true'` for every wine (not scraped, a constant), which today silently grants
every non-ÁTVR wine a real +10% score bonus (`wines.sql:58-61`). In an evidence-ledger world this
isn't a bug to patch, it's a source that was never allowed to assert a fact it can't actually
observe — the ledger would simply have no organic evidence for those rows, and the UI would say
"unknown" instead of quietly rewarding a fabricated "yes."

---

## 06 — What the scoring system should score

### Two scores, not one

The brief's instinct here is correct and worth defending strongly: quality and value-for-money are
different questions, and today's system answers only one blended one. `recommendation` multiplies
`power(rating, 3.8)` — an extremely aggressive exponential curve on a 0–5 crowd rating — by a
price/volume term and an organic multiplier, caps it, and calls the result a single 0–1
"recommendation." A €12 wine rated 4.1 and a €40 wine rated 4.6 could land on the same number for
entirely different reasons, and nothing in the export tells a user which reason applied.

**Quality Score — Vintage-level**
- Answers: "is this good wine," independent of what it costs anywhere.
- Aggregates weighted evidence from the ledger (§05): crowd ratings, eventually critic data,
  eventually first-party user ratings.
- Always carries a visible confidence/coverage indicator — "based on 3 sources, high confidence" vs.
  "one source, 4 reviews, low confidence" — not just a number.
- Recomputes as new evidence arrives; a wine's quality reading should improve as it accumulates more
  corroborating sources, the same way a Match's confidence should.

**Value Score — Listing-level**
- Answers: "is this a good deal, at this retailer, today."
- Quality Score of the matched Vintage, relative to this Listing's price and bottle size.
- Changes constantly and independently of quality — a price drop at Sante raises Value without
  touching Quality.
- Undefined (not zero) when no Vintage match exists yet — see §07 on why "no score" must be a
  legitimate, visible state rather than exclusion from the catalog.

A useful test for whether this split is real: after it ships, it should be possible to ask "show me
the highest-quality wines regardless of price" and "show me the best deals right now" as two
genuinely different queries returning different results — something the current single
`recommendation` column cannot do even in principle, because price is already baked into it before
it ever reaches the export.

> **Worth challenging directly.** The `rating_count_index` tiering (<100 reviews → ×0.8, 100–500 →
> ×0.9, …) is a reasonable instinct — low-sample ratings are less trustworthy — but hardcoding it as
> a multiplier on the final score conflates "less certain" with "worse." A wine with 40 five-star
> Vivino reviews isn't necessarily lower quality than one with 400 — it's just a number Godvinkaup
> should trust less confidently. That's a confidence band on the Quality Score, not a quality
> penalty. The same information, modeled as uncertainty instead of a discount, produces a more
> honest UI: "4.6★, based on 40 reviews (limited data)" rather than a silently deflated 4.1.

---

## 07 — Retailer matching

### Candidate → confidence → gate, continuously re-run

The brief is right that canonical wines should be optional and confidence-driven — but the
architecture needs to go one step further than "match once, keep the result forever." Identity
resolution should be a standing, re-runnable process, because confidence is a function of
accumulated evidence, and evidence keeps arriving. A listing that scores 0.6 today against a
Vintage might legitimately cross a threshold six months from now once three more retailers list the
same wine and a producer canonicalization pass resolves a spelling variant — the system should be
able to notice that without a human re-triggering anything.

**Fig. 3 — matching pipeline, replacing the current single fuzzy-match-and-insert step**

```text
  new / re-evaluated LISTING
        │
        ▼
  1. CANDIDATE GENERATION  (deterministic, cheap)
     exact GTIN/barcode if ever available → producer+vintage+volume block
     → trigram / phonetic similarity over name+producer
        │
        ▼
  2. CONFIDENCE SCORING    (the current SequenceMatcher logic, kept —
                             it's a reasonable first-line signal — but its
                             output is now WRITTEN, not discarded)
        │
        ├── ≥ high threshold  ──▸ auto-link, MATCH row confidence=high
        │
        ├── medium band       ──▸ MATCH row confidence=medium
        │                          → surfaced as "possibly the same wine,"
        │                            catalog shows listing as its own
        │                            Vintage until resolved — never
        │                            silently merged
        │
        └── low / no candidate ─▸ no MATCH row.
                                   Listing still ships with its own
                                   Value Score once it has a Quality
                                   Score from any source — it is NOT
                                   excluded from the catalog the way an
                                   unmatched wine is today (wines.sql
                                   inner join, TD-05)
        │
        ▼
  3. HUMAN REVIEW QUEUE (medium-confidence, high-traffic wines first)
        │
        ▼
  4. RE-SCORE on a schedule as new listings/evidence accumulate
```

Two changes here matter more than the diagram suggests. First, an unmatched listing is a normal,
permanent state, not a temporary failure — it gets its own Quality Score once any evidence source
(retailer description, future critic feed, eventual user ratings) applies to it, rather than
waiting in limbo for a Vivino hit that a 15-lookups-a-day scraper (`scrape_vivino_ratings.py:211`)
may never get to. Second, "medium confidence" is a genuine third catalog state, not a binary
merged/rejected — this is precisely the mechanism that makes "false positives worse than
duplicates" an enforceable property of the system rather than a value statement in a design doc.

---

## 08 — Target architecture

### Same skeleton, new organs

Airflow-for-orchestration and dbt-for-transformation should survive essentially unchanged as a
division of labor — this is a boring, correct choice worth keeping boring. What needs to be added
is an identity/evidence layer between "landing" and "marts" that doesn't exist today at all, and a
way out of the current publishing model (a full-table JSON dump git-pushed to a separate repo once
a day) as the platform starts wanting live queries, personalization, and its own interaction data.

**Fig. 4 — target-state layers (5-year view)**

```text
 SOURCES        ÁTVR · Sante · Uva · (more retailers over time)
                Vivino · (2nd rating source, eventually)
                Godvinkaup's own users  ◂── new, first-party
                     │
                     ▼
 LANDING        raw per-source rows, unchanged in shape —
                but SNAPSHOTTED, not dropped/recreated (TD-11 fix)
                     │
                     ▼
 CATALOG        LISTING dimension (SCD2 price/stock history)
 (dbt)          + RETAILER dim  (replaces hardcoded seller strings)
                     │
                     ▼
 IDENTITY       candidate generation → confidence scoring → MATCH ledger   ◂── new layer
 (Python +      (deterministic first, LLM-assisted for the residual,
  evidence      human queue for medium confidence)
  ledger)             │
                     ▼
 EVIDENCE       append-only RATING ledger (any source, any subject)        ◂── new layer
                     │
                     ▼
 SCORING        Quality Score (Vintage)  +  Value Score (Listing)          ◂── split, versioned
 (dbt, versioned, tested — currently zero dbt tests on any of this, TD-10)
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
 SEARCH                    SERVING LAYER
 embeddings → Qdrant       API / read-replica, queried live               ◂── replaces the
 (keep, already works)     by the website — not a daily JSON snapshot        daily git-push export
                                  │
                                  ▼
                           INTERACTION CAPTURE                             ◂── new, first-party
                           views / saves / clicks-to-retailer
                           feeds back into the evidence ledger
```

Nothing here requires abandoning Postgres, Airflow, or dbt. The "platform" the brief asks about is
mostly a modeling and provenance problem wearing an infrastructure costume — the boxes that need to
be genuinely new are the identity/evidence layer and, later, the interaction-capture loop. Both can
be built incrementally inside the existing stack.

---

## 09 — Alternative architectures considered

### Three roads not taken, and why

*Considered and rejected (or partially adopted) in favor of the target architecture above*

| Option | Pitch | Why not (or not alone) |
|---|---|---|
| **A — Patch in place** | Change the Vivino `INNER JOIN` to a `LEFT JOIN`, add a second rating source, ship. Cheapest possible fix to the acute risk. | Doesn't touch the listing/vintage/wine grain problem (TD-16), so quality and value stay conflated and matching stays a one-shot silent process. Legitimate as a **0–3 month stopgap** while the real model is built — not a destination. |
| **B — License a commercial wine reference database** | Buy GTIN-level wine identity data instead of building fuzzy matching in-house; shortcuts the "well-known wine" half of the catalog. | Real option worth pricing out, but it won't cover the long tail that's specific to the Icelandic market (small imports, private labels) — exactly the wines with no Vivino match today. Best used as a **hybrid**: licensed data for the easy 80%, the identity pipeline in §07 for the local 20% that's actually Godvinkaup's differentiation. |
| **C — Full event-sourced catalog** (event-source everything) | Treat every field, not just identity/ratings, as an immutable event log; rebuild all state by replay. | Overkill for facts with no real epistemic uncertainty — a listing's current price doesn't need CQRS, it needs a snapshot. Adopted **narrowly**: only the identity/evidence layer (§05, §07) actually has the kind of uncertainty that justifies an append-only ledger; the catalog layer stays a conventional dimensional model with SCD2 history. |

---

## 10 — Risks

### What could go wrong with this direction

- **Cold start on first-party data.** "Own the signal" (Principle 7) is a multi-year payoff; for the
  first year or two the Quality Score is still mostly borrowed evidence. The roadmap has to be
  honest about this rather than implying first-party data solves anything on day one.
- **Scraping fragility is systemic, not Vivino-specific.** ÁTVR's AJAX endpoint, Sante's Shopify
  JSON, and Uva's WooCommerce API are all unofficial, undocumented surfaces that can change without
  notice — `scrape_atvr_descriptions.py` already depends on one hardcoded ASP.NET element id
  (TD-14). Diversifying evidence sources reduces dependence on any one of them but doesn't make any
  of them durable.
- **Legal exposure on scraping itself**, independent of "Vivino isn't viable" — worth a deliberate
  look at retailer/Vivino terms of service before scaling acquisition further, not just a technical
  risk.
- **False-merge risk doesn't go to zero**, it goes to "gated by a threshold a human chose." The
  threshold itself becomes a product decision with real consequences and needs monitoring (drift in
  match quality over time), not a one-time tuning exercise.
- **Team size.** This repository shows the signature of a single maintainer under time pressure —
  four near-duplicated scraper files (TD-06), two different hardcoded passwords for the same host
  (TD-01), a comment reading "(TEMPORARY) Later: move to Airflow Variables" still in place. A
  five-year platform roadmap has to be sized to that reality: incremental, always-shippable phases,
  not a big-bang rebuild.
- **LLM cost/latency at catalog scale** if extraction or normalization is run naively per-row on
  every `dbt run` rather than incrementally on new/changed rows only.

---

## 11 — Open questions

### Decisions only the product owner can make

- **Business model.** Is Godvinkaup an affiliate/referral engine sending clicks to retailers, a
  media/content site, or eventually a personalized shopping assistant with accounts? This determines
  how much of the "own the signal" roadmap (§01, Phase 3+) is actually in scope versus nice-to-have.
- **Legal posture on scraping** ÁTVR/Sante/Uva/Vivino long-term — any appetite for official
  data-sharing relationships instead, given ÁTVR is a state monopoly?
- **Budget for a licensed wine reference dataset** (Alternative B, §09) — would meaningfully change
  how much custom matching infrastructure is worth building versus buying.
- **Realistic manual-curation bandwidth.** The human-review queue in §07 only works if someone
  actually reviews it; today's Vivino pipeline processes 15 lookups a day with zero review. What
  cadence is sustainable?
- **Product tolerance for "no score yet."** Does the catalog show unmatched/low-confidence wines
  with a visible "limited data" state, or hide them until resolved? This is a UX call, not a data
  call, and it determines whether fixing the `INNER JOIN` actually grows the visible catalog or just
  adds noise.
- **Should Fantrax stay on shared infrastructure?** Not urgent, but the wine platform and an
  unrelated fantasy-football pipeline currently share one Postgres instance and one Airflow
  deployment — worth a deliberate yes/no as "platform" stops being a loose word.

---

## 12 — Roadmap

### Four phases, each independently shippable

**Phase 0 — weeks — Stop the bleeding**
Rotate the credentials committed in `scrape_vivino_ratings.py`, `scrape_sante_wines.py`, and
`docker-compose.yml` (TD-01/02); fix the Sante/Uva hardcoded `is_organic='true'` bug that's actively
inflating scores today; re-enable the commented-out cross-DAG sensors (TD-09); prefix all retailer
IDs to remove the possible key collision in `dim_wines` (TD-15); switch the Vivino join to `LEFT`
with explicit null-handling as an interim stopgap so the catalog stops silently capping while §03–§07
are built.

**Phase 1 — 1–2 quarters — Grain and evidence**
Introduce Wine / Vintage / Listing / Match as real entities; stand up the append-only rating
evidence ledger (stop the in-place `UPDATE` that's destroying rating history today); split
`recommendation` into Quality Score and Value Score; add dbt snapshots for price/availability
history (TD-11); add the dbt tests and source-freshness checks that currently don't exist on any
Vivino-derived column (TD-10).

**Phase 2 — 2–4 quarters — Diversify and expose**
Add a second quality-evidence source (a second crowd source, a licensed reference dataset, or both
— see §09 Alternative B); build the medium-confidence human review queue from §07; replace the
daily JSON-to-git-push export with a queryable API/read-replica so the website reads live state
instead of a snapshot.

**Phase 3 — year 2+ — Start owning the signal**
Capture first-party interaction data (views, saves, clicks-to-retailer) on the Godvinkaup site
itself; begin blending it into the evidence ledger at low initial weight; add LLM-assisted
structured extraction of tasting notes/style from retailer descriptions, tagged "machine-extracted"
in the evidence ledger rather than presented as fact.

**Phase 4 — year 3–5 — Personalize, and stop needing any one source**
Personal taste profiles built on owned interaction + rating data; Quality Score is by now a
genuinely multi-source, partly-owned aggregate, so losing any single external source (Vivino
included) degrades confidence rather than breaking the catalog. Revisit whether Fantrax should
still share infrastructure now that "platform" is a load-bearing word.

---

## 13 — Keep vs. retire

### What deserves to survive almost unchanged, and what should disappear

**Keep**
- Airflow for orchestration, dbt for transformation — the split itself, not every current DAG.
- The extract → land → union → mart pipeline shape.
- Multi-retailer sourcing (ÁTVR + Sante + Uva) — the catalog breadth is a real asset worth growing,
  not replacing.
- Embeddings + Qdrant for semantic search/discovery — a good use of the technology, unrelated to the
  identity/scoring problems above.
- The stated coding philosophy in `AGENTS.md` — correctness over cleverness, dbt over Python for
  business logic — it's already right.

**Retire**
- Hardcoded credentials in source (multiple files, multiple secrets).
- The single blended `recommendation` formula and its bare `power(rating, 3.8)` dependence on one
  vendor's scale.
- `DROP TABLE ... CASCADE`-every-run landing tables — replace with snapshots before any trend
  feature is attempted.
- The Vivino `INNER JOIN` as a catalog gate, and the `LIMIT 15`/day matching cadence as a permanent
  architecture (fine as scrape politeness, wrong as the only path to full coverage).
- Per-retailer-listing as the terminal grain for any score.
- The daily flat-JSON git-push export, once a queryable serving layer exists.
- Broad `except Exception: print(...)` swallowing that lets partial failures report green in
  Airflow.

---

Five years from now, the tooling in this stack will probably look almost identical to today's. What
will have changed — what actually makes this a platform instead of a script — is that every number
on the site will trace back to a source, a confidence, and a timestamp, and losing any one of those
sources will make the platform less certain, never mute.

*Godvinkaup ETL — discovery-verified architecture memo — no code modified — read-only exercise.*
