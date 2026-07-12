# Scoring Philosophy

**The constitution of the Godvinkaup scoring engine.**

This document is not the scoring model. It does not propose a formula, a weighting scheme, a
threshold, or an algorithm. Its job is to define the principles that any future scoring model —
whichever engineer builds it, whichever techniques it uses, however many times it gets rewritten —
must remain faithful to. Implementations should be judged against this document, not the other way
around.

It builds on two prior exercises in this repository: `docs/architecture/platform-architecture.md`
(the target architecture — entities, evidence ledger, matching pipeline) and
`docs/architecture/scoring-evidence-inventory.md` (the catalogue of what evidence actually exists
and how trustworthy each piece is). Where this document says "quality," "confidence," "value," or
"evidence," it means exactly what those documents established; where it cites a current-system
example (the `rating_count_index` tiering, the Sante/Uva `is_organic` hardcoding, the Vivino inner
join), it is drawing on facts verified in `docs/discovery/`.

Every principle below is labeled **Established**, **Recommendation**, or **Open question**:

- **Established** — settled; the platform's other documents already depend on it, and this document
  found no reason to disagree. Treat these as load-bearing.
- **Recommendation** — this document's best answer, offered with reasoning, but not yet tested
  against a real implementation. A future architect can revisit these with evidence, not just
  preference.
- **Open question** — a genuine fork that only a future decision (product, legal, or empirical) can
  resolve. Listed explicitly so nobody mistakes silence for an answer.

---

## Purpose

Godvinkaup is building an independent estimate of wine quality to replace a total dependency on
Vivino. The purpose of that estimate is not to be the most numerically accurate predictor of a
wine's "true" quality achievable — it is to be a synthesis of disclosed, checkable evidence that a
user can *audit and trust*, even when it's wrong.

**Established.** The primary success metric for the scoring engine is trust, not accuracy. A score
that is slightly less precise but fully explainable is worth more to this platform than a score that
is marginally more accurate but opaque. This follows directly from the platform's founding problem:
Godvinkaup's original sin was never that Vivino's rating was inaccurate — it was that the platform
had no independent judgment of its own and no way to explain what it was showing. A more accurate
black box repeats the same failure with better numbers.

**Established.** The platform must never claim to have tasted a wine, or imply firsthand sensory
knowledge. Every quality estimate is a secondhand synthesis of other people's and other systems'
judgments — crowds, critics, regulatory classifications, structural data — weighted by how much
they should be trusted. The language the platform uses about itself (in scores, in explanations, in
UI copy) should reflect this honestly: "estimated," "based on," "evidence suggests," never "this
wine is" stated as unqualified fact.

---

## Non-goals

Stated explicitly so future scope creep has something to point at:

- **Not a personalization engine.** Quality is an estimate of general, evidence-backed merit — not
  a prediction of whether a specific user will personally like a specific wine. Personal taste
  modeling (Phase 4 of `platform-architecture.md`) is a separate, later capability built *on top of*
  an honest quality estimate, not a substitute for one. Conflating the two would make the score
  mean something different for every user, which breaks explainability and reproducibility both.
- **Not an authenticity or provenance-verification system.** The score does not attest that a bottle
  is genuine, correctly stored, or unadulterated. That is a supply-chain/legal question, out of
  scope for a quality estimate built from catalog and review data.
- **Not an engagement-optimization system.** The score's job is never to maximize clicks, dwell
  time, or conversion. Popularity-adjacent signals (review counts, future first-party behavioral
  data) are treated as *confidence* inputs at most, never as a proxy objective the model is trained
  to increase — see Fairness, below.
- **Not a single blended number.** Quality, Confidence, and Value are irreducible; a scoring engine
  that outputs one score per wine, with price already baked in, does not satisfy this philosophy no
  matter how well-calibrated that single number is.
- **Not a finished, static artifact.** A "final" score that never changes is a sign the evidence
  pipeline has stopped, not a sign of confidence. See Versioning.
- **Not a substitute for professional sommelier judgment for high-stakes decisions** (cellar
  investment, event sourcing at scale) — the platform estimates likely quality from available
  evidence; it does not replace expert tasting for decisions where the cost of being wrong is high.

---

## Core principles

The eight principles below were supplied as already-established; each is restated here with the
reasoning that grounds it, plus, where useful, a sharpening note. None are contested — no principle
below records a disagreement — but several needed a boundary drawn so the "constitution" clause
outlives the current implementation. Two additional principles have been added at the end, because
the source documents depend on them just as load-bearingly as the original eight.

**1. Quality, Confidence, and Value are separate concepts. — Established.**
This is the single most important modeling decision in the whole platform. Every distortion in the
current system (`recommendation = power(rating, 3.8) × price/volume term × organic multiplier`)
traces back to collapsing these into one number. They must remain three separately-computed,
separately-displayed values, even in a UI that later chooses to show only one of them prominently.

**2. Retailer listings are first-class entities. — Established.**
A listing (a specific retailer's SKU, at a specific price, on a specific day) is real and valuable
even when it cannot be matched to any canonical wine. The current system treats an unmatched
listing as if it doesn't exist (the Vivino inner join); this platform treats it as an entity with
its own identity and, per Principle 8 below, its own confidence-labeled evidence.

**3. Canonical wine entities are optional. — Established.**
A "Wine" (producer + label, independent of vintage or retailer) is a convenience for aggregating
evidence across listings and vintages — not a prerequisite for scoring. A listing with no confident
match to any canonical wine should still be scorable from whatever evidence attaches to it directly.
*Sharpening note:* "optional" means optional to *create*, not optional to *reason about*. Even an
unmatched listing is conceptually a wine of exactly one listing; the schema doesn't need to
materialize that as a row, but the scoring logic should not special-case "no canonical match" as an
error state — it's a normal, common point on the confidence spectrum, not an edge case.

**4. False merges are worse than duplicate listings. — Established.**
A duplicate is an inconvenience a user can visually filter past. A false merge silently gives one
wine another wine's reputation — the user has no way to detect this from the UI, which makes it a
trust failure, not a data-quality footnote. Every identity-resolution threshold in the system should
be set with this asymmetry in mind: it is correct to leave two listings unmerged when uncertain, and
incorrect to merge them "for a cleaner catalog."

**5. Every score must be explainable. — Established.**
If a score's derivation cannot be reconstructed and shown to a user in plain language, it should not
ship. This isn't a UI nicety — it's the mechanism that makes every other principle checkable from
outside the system. An unexplainable score is unfalsifiable, and an unfalsifiable score cannot be
trusted, however accurate it happens to be.

**6. Every score must be reproducible. — Established.**
The same evidence, evaluated by the same model version, must produce the same score, every time.
This is what makes "why did this change" answerable — the answer is always either "new evidence
arrived" or "the model version changed," never "it's probabilistic" or "we're not sure." See
Versioning for how this interacts with evidence that legitimately updates over time.

**7. Every score should preserve provenance. — Established.**
Every fact feeding a score — a rating, a classification, an extracted attribute — carries its
source, the method used to obtain it, and when it was retrieved, for the lifetime of the system. A
score is only as trustworthy as its ability to answer "where did this come from," and provenance
that isn't captured at ingestion time is provenance that can never be reconstructed later.

**8. Missing evidence should generally reduce confidence rather than automatically reduce quality. —
Established.**
This is the principle the current system violates most concretely: `rating_count_index` treats a
low review count as a reason to lower the score, when it is actually a reason to trust the score
less. A wine with 40 five-star reviews is not worse than one with 400 — it is simply a number the
platform should stand behind less firmly. *Sharpening note on "generally":* this is not an
absolute. If evidence about a specific, checkable fact is missing where it should exist — e.g. a
producer whose other vintages are consistently poorly reviewed now has one exceptionally short,
sparse review — the *absence relative to expectation* can be informative and, evaluated carefully,
is fair to fold into quality. What must never happen is treating "we haven't looked much" and "we
looked and it wasn't good" as the same signal. The default posture is confidence reduction; a
quality adjustment from absence requires an explicit, evidenced case for why the absence itself is
informative.

**9. Value must never influence Quality. — Recommendation (implied by Principle 1, made explicit).**
Price is the denominator of Value by definition. If it is also allowed to influence Quality — even
indirectly, even as a plausibility check ("this is expensive, so it's probably good") — the score
becomes circular and self-confirming, and an "independent" scoring system stops being independent.
This principle is listed separately from Principle 1 because it is the specific failure mode most
likely to be reintroduced by accident (e.g., a future engineer using price as a feature to help
impute a missing quality signal). It should be treated as a hard boundary, not a tunable weight.

**10. An AI is a candidate generator and an explainer — never a silent merge authority. —
Recommendation (carried forward from `platform-architecture.md` §04).**
Elaborated fully in AI Principles, below. Stated here because it is as load-bearing as the other
nine: the moment an AI model is allowed to assert identity or fact without a disclosed, checkable
confidence value attached, Principle 4 (false merges are worse than duplicates) becomes
unenforceable in practice, no matter what the document says.

---

## Definitions

**Wine** — a producer's label, independent of vintage (e.g., "Château X Réserve"). A convenience
grouping, optional to materialize (Principle 3).

**Vintage** — a specific year's (or non-vintage) release of a Wine. This is the grain at which
**Quality** is estimated, because quality genuinely varies year to year and a single "producer
quality" number would erase that.

**Listing** — a specific retailer's offer of a Vintage: a price, a bottle size, a stock state, on a
specific day. This is the grain at which **Value** is estimated. A Listing may exist with no
confirmed link to any Vintage or Wine (Principle 2).

**Match** — the evidenced, confidence-scored claim that a given Listing corresponds to a given
Vintage. A first-class, auditable fact — never an implicit side effect of a join.

**Evidence** — any disclosed, sourced fact that could inform Quality, Confidence, or Value. Never
stored as a bare value; always carries source, method, timestamp, and (where applicable) sample
size.

---

## Quality

**What Godvinkaup is estimating.** Quality is an estimate of a Vintage's likely sensory and
craftsmanship merit, synthesized from disclosed third-party evidence — crowd sentiment, critic
judgment where available, and structural/regulatory signals that correlate with production
standards. It is explicitly *not* a claim about how any specific user will experience the wine.

**Established.** Quality attaches to the Vintage, not the Listing, the Wine, or the retailer. Two
listings of the same Vintage at different retailers share one Quality estimate; two vintages of the
same Wine do not.

**Recommendation.** Quality should be modeled, and communicated, as a *range with a most-likely
point*, not a bare scalar — even before any UI decides how to visualize that. Treating quality as a
single deterministic number invites exactly the overconfidence failure mode this document warns
against in Failure Modes, below. The scoring engine's internal representation should carry
uncertainty even if a future UI chooses to collapse it to one displayed number.

**Out of scope for Quality** (restated from Non-goals, specific to this axis):
- Personal taste fit.
- Price-worthiness (that's Value).
- Authenticity/provenance verification.
- Health, allergen, or nutritional characteristics.
- Aesthetic/philosophical stances not grounded in disclosed evidence (e.g., a blanket "natural wine
  is inherently better/worse" prior).

**Open question.** Should Quality ever be estimated for a Vintage with literally zero evidence,
purely by inheritance from the Wine's or Producer's track record (Principle 9's Producer signal from
`scoring-evidence-inventory.md`)? This document takes no position — it is legitimate architecture
either way, but the choice materially affects how "confidence: none" states are handled downstream
and should be decided deliberately, not by default.

---

## Confidence

**Why it's first-class, not a footnote.** A quality number without a confidence value is a claim
with the epistemics hidden. Confidence exists so the platform can say, honestly, "here's our best
estimate, and here's how much you should trust it" — which is a fundamentally different, more
honest statement than a single number pretending certainty it doesn't have.

**Established.** Confidence is driven by the volume, diversity, reliability, and recency of
corroborating evidence — not by the value of the estimate itself. A high quality estimate built on
one thin source is *lower* confidence than a middling estimate corroborated by three independent,
reliable sources.

**Recommendation.** Confidence should be represented as a small number of meaningful, explainable
tiers (e.g., something like "strong / moderate / limited evidence") backed by a visible reason, not
as a bare probability or percentage exposed to end users. A number like "confidence: 0.71" invites
false precision about something that is itself an estimate of an estimate; a labeled tier with a
one-line reason ("based on one source, 12 reviews") is more honest and more explainable at the same
time. Internally, the engine may compute confidence numerically — the recommendation is about what
gets *shown*, not what gets *computed*.

**Recommendation.** Uncertainty should prevent a numeric quality score from being shown — replaced
with an explicit "not enough evidence yet" state — below some evidence floor (e.g., a single
low-reliability, unconfirmed source with no corroboration). This document deliberately does not
specify where that floor sits; it specifies that the floor must exist, and that below it, honesty
requires withholding a number rather than publishing a guess dressed as an estimate. A visible
"insufficient evidence" state is a *feature*, directly required by Principle 2 (listings without
canonical matches still deserve a place in the catalog) and Principle 8 (absence should show up as
low confidence, not a fabricated number).

**Open question.** Should confidence ever be allowed to *decay* over time even when no new
contradicting evidence arrives — i.e., should a rating from three years ago count for less today
purely due to staleness, independent of whether anything about the wine actually changed? This
interacts with Versioning (below) and is worth resolving with real evidence about how often quality
signals genuinely go stale, not by assumption.

---

## Value

**How Value differs from Quality.** Quality asks "is this good wine." Value asks "is this a good
deal, right now, at this specific retailer." Value is a *relationship* between a Quality estimate
and a price — it does not exist independently of both terms, and it is not itself evidence about the
wine's merit.

**Established.** Value must always remain Listing-specific, never Vintage- or Wine-specific. The
same Vintage can be simultaneously a excellent value at one retailer and a poor one at another, on
the same day — collapsing Value up to the Vintage level (as today's single `recommendation` column
effectively does, since it's computed once per matched row) destroys exactly the information a
price-comparison-minded user is asking for.

**Established (restated from Principle 9).** Value is downstream of Quality; Quality must never be
downstream of Value. This ordering constraint is the guard against circularity described above and
is treated as non-negotiable.

**Recommendation.** Value should be undefined, not zero, for a Listing with no Quality estimate
available (per Principle 3's "no canonical match" case). A Value of zero implies "known to be a bad
deal"; the honest state for "we don't know the quality yet" is "no Value estimate," displayed and
explained as such — consistent with the Confidence principle above.

---

## Evidence

**What deserves trust.** Evidence earns trust along three largely independent axes: disclosed
methodology (do we know *how* this fact was produced), verifiability (can a user or engineer check
it against a named source), and sample size where applicable (one data point is weaker than a
thousand, all else equal). Evidence with all three — a critic's disclosed scoring rubric, a large
crowd sample, a regulatory classification — deserves the most weight. Evidence missing all three —
an unattributed superlative in marketing copy — deserves essentially none, as raw evidence; it may
still be useful as *raw material to extract other, separately-verified evidence from* (see the
Retail descriptions entry in `scoring-evidence-inventory.md`), but the extraction output is what
gets trust-graded, not the marketing copy itself.

**Established, carried from `scoring-evidence-inventory.md`.** Some evidence should never directly
influence Quality: retail price, bottle size, style/preference attributes (sweetness, body, ABV),
verbatim retailer marketing copy, unweighted competition medals, and — critically, because it is a
live example, not a hypothetical — certification status (organic/biodynamic) used as a taste proxy.
The Sante/Uva `is_organic='true'` hardcoding is not a bug to patch quietly; it is a standing example
of exactly the category of mistake this principle exists to prevent: a source asserting a fact it
cannot actually observe, silently rewarded as if it were quality evidence.

**Established, carried from `scoring-evidence-inventory.md`.** Some evidence should only influence
Confidence, never Quality directly: review/sample counts, extraction-method reliability (a
heuristically-parsed vintage vs. a structurally-sourced one), match certainty for producer/entity
canonicalization, and corroboration density (how many independent sources agree). The general test:
if a fact tells you *how sure to be* about another fact, it belongs to Confidence; if it tells you
something new about the wine itself, it may belong to Quality.

**Recommendation.** Every piece of evidence entering the system should be tagged with its
acquisition method (structured API field, heuristic extraction, AI-assisted extraction, human
review) at ingestion time, not reconstructed later. Reliability assessment becomes guesswork the
moment this tagging is skipped even once, because there is no way to distinguish "this heuristic
value happens to look clean" from "this was actually a structured field" after the fact.

---

## Explainability

**Established.** Every score the platform surfaces must be able to answer, at minimum, the six
questions the product brief poses: *why, based on what evidence, under which assumptions, which
model version, how recent, how confident.* A score that cannot answer all six on demand is not
ready to ship, regardless of how it performs on any accuracy metric.

**Recommendation — the explanation must be generated from the same computation that produced the
score, never reconstructed afterward by a separate process.** This is the single most important
engineering discipline this document asks for, because it's the one most tempting to skip: it would
be easy to compute a score numerically and then ask a language model to "write an explanation" for
it after the fact. That produces a plausible-sounding narrative that is not actually guaranteed to
match what the score's inputs were — a hallucination risk stacked directly on top of the number
users are meant to trust most. The explanation is not prose *about* the score; it is a structured
readout *of* the score's actual inputs, optionally rendered into prose afterward, but never
independently generated.

**Recommendation.** The six required elements map onto concrete, storable objects, not free text:

| Question | What answers it |
|---|---|
| Why? | The ranked list of evidence items that most moved the estimate |
| Based on what evidence? | The evidence ledger entries actually used, each with its own source |
| Which assumptions? | The model/methodology version's documented assumptions (e.g., how sources are weighted by class, not by specific number) |
| Which version? | A stable model-version identifier, stamped on every score at computation time |
| How recent? | The retrieval timestamp of the most recent, and the oldest, evidence used |
| How confident? | The confidence tier and its stated reason (see Confidence, above) |

**Open question.** How much of this explanation surface should be shown by default versus behind a
"why this score" expansion? This is a UX decision downstream of the philosophy, not a philosophical
one — but it's listed here because the underlying data must exist regardless of the UI's eventual
choice, and it would be a mistake to build the scoring engine without it on the assumption that "we
can add explainability later."

---

## AI principles

Directly inherited from `platform-architecture.md` §04, restated as scoring-specific principles.

**Established. The core rule: an AI model may generate candidates and explanations; it may never be
the sole, silent authority on a fact that becomes load-bearing evidence.** A fluent, confident
model output ("yes, this is the same wine") is more dangerous than a visibly uncertain deterministic
score, because fluency reads as certainty to a human reviewer even when the underlying confidence is
low. Every AI-assisted output must carry its own explicit confidence value into the evidence ledger,
exactly like any other evidence source — it does not get a pass because it "sounds sure."

**Recommendation — appropriate uses of AI:**
- Generating *candidates* for identity matching (a shortlist to be confidence-scored, not a decision).
- Extracting structured facts from unstructured text (tasting notes, grape percentages, style)
  where no structured field exists — tagged explicitly as machine-extracted, at a confidence no
  higher than the extraction method warrants.
- Assisting free-text canonicalization (producer names, region spellings) where deterministic rules
  fail, still gated by a confidence threshold before being trusted.
- Semantic search and discovery ("find me something like this") — a fundamentally different task
  from scoring, since a bad semantic match costs a user a mildly irrelevant search result, not a
  trust-breaking false merge.
- Rendering a structured explanation object (see Explainability) into readable prose — provided the
  underlying facts are fixed before generation, so the model is formatting, not authoring, the
  explanation.

**Recommendation — tasks that should always remain deterministic**, regardless of how good AI
matching gets: unit and currency normalization; aggregation and weighting logic itself, once
evidence and confidence values are established; orchestration, scheduling, retries; anything where a
rule can be written and audited directly, since a deterministic rule is definitionally more
explainable than a learned one and this platform trades accuracy for explainability by design (see
Purpose).

**Established — tasks that should never use AI:** asserting price, ABV, volume, availability, or any
other fact a retailer feed states directly and verifiably (there's no ambiguity for a model to
usefully resolve, and any AI involvement there is pure added risk); merging two catalog identities
into one canonical entity at anything other than the highest confidence tier without a human in the
loop (Principle 4); and generating an explanation for a score using facts that were not actually
part of that score's computed inputs, under any framing — this is the hallucination boundary that
must never be crossed, because it directly forges the evidence trail Principle 7 depends on.

---

## Fairness

The platform's independence is only meaningful if it doesn't quietly re-import the biases that come
from tracking whichever wines are already famous, expensive, or well-marketed.

**Recommendation — guard against favoring famous producers.** A producer's track-record prior
(`scoring-evidence-inventory.md`, "Producer") must be built from the *number and quality of that
producer's actual scored Vintages*, not from fame, mention frequency, or how many retailers carry
them. A producer that is well-known but thinly evidenced within Godvinkaup's own catalog should
receive a track-record prior no stronger than the evidence actually supports.

**Recommendation — guard against favoring expensive wines.** This is enforced structurally by
Principle 9 (Value must never influence Quality) rather than by a bias-correction step — the
cleanest fairness guarantee is that price is never an input to Quality in the first place, so there
is nothing to correct for after the fact.

**Recommendation — guard against favoring prestigious regions.** Per `scoring-evidence-inventory.md`,
raw region/country must never be a direct Quality input on its own — at most a weak Confidence
prior when little else is known, clearly labeled as such. Appellation/classification (a legally
encoded production standard) is a materially different, stronger signal than reputation-by-region
and should be preferred wherever available, precisely because it's a substantive fact rather than a
prestige association.

**Recommendation — guard against favoring highly marketed wines.** Review/mention *volume* is a
Confidence input, never a Quality input (Principle 8 and the Evidence section, above). A heavily
marketed wine with many reviews should get a *tighter* confidence band around whatever its quality
evidence actually shows — not a higher quality estimate simply because more people are talking about
it. Awards and competition medals should be discounted by competition rigor/prestige rather than
counted at face value, since an unweighted medal count structurally rewards wines entered into many
(possibly low-bar) competitions over wines that simply weren't submitted anywhere.

**Recommendation — remaining fair to lesser-known producers.** A wine with thin evidence should
receive an honestly *lower-confidence* estimate, not an artificially *lower-quality* one. Concretely:
a small producer's single wine with five excellent, credible reviews should never score worse than a
large producer's wine with five hundred mediocre ones just because of the sample-size difference —
the sample-size difference belongs entirely to Confidence. This is Principle 8 applied as a fairness
mechanism, not just an accuracy one: the platform's default posture toward unfamiliar producers must
be "we don't know enough yet," never "unfamiliar, therefore penalized."

**Open question.** Should the platform ever apply an *explicit* counter-weighting to compensate for
structural imbalance in evidence availability (e.g., large international producers being
over-represented in crowd-rating databases relative to small Icelandic-market imports)? The
Recommendations above prevent *active* favoritism; whether the platform should go further and
actively favor under-evidenced listings to correct a structural imbalance is a product/values
decision this document does not resolve.

---

## Failure modes

Not every mistake carries the same weight. Distinguishing acceptable from unacceptable failure is
what makes "maximize trust" an operational principle instead of a slogan.

**Acceptable:**
- **Duplicate listings.** A UX inconvenience, per Principle 4 — fixable without having damaged
  trust in the meantime.
- **A wine sitting in "no score yet" or "limited evidence" for a long time.** Honest absence of a
  claim is always acceptable; it is the alternative (a fabricated or overconfident claim) that isn't.
- **A well-evidenced, honestly-labeled quality estimate that later evidence shows was somewhat off.**
  Normal estimation error, provided the confidence label at the time was itself honest. The system
  is allowed to be wrong; it is not allowed to have been dishonest about how sure it was.
- **A slow-to-resolve medium-confidence match sitting in a human review queue.** A visible, honest
  "possibly the same wine" state, per `platform-architecture.md` §07 — this is the system working as
  designed, not a failure.

**Unacceptable:**
- **False entity matches presented at high confidence.** The single worst failure mode in the whole
  system, per Principle 4 — it silently transfers one wine's reputation onto another with no visible
  trace for a user to catch.
- **Overconfident scores.** A confidence label that overstates the underlying evidence is a lie
  about the system's own epistemics, independent of whether the point estimate happens to be
  accurate.
- **Misleading explanations** — an explanation that cites evidence not actually used in the
  computation, omits materially contradicting evidence, or was generated independently of the
  score's real inputs (see Explainability). This is a distinct, and arguably worse, failure than an
  inaccurate score, because it corrupts the one mechanism (explainability) meant to let users catch
  every other kind of error.
- **Stale evidence presented without disclosed recency.** Evidence going stale is normal and
  expected; presenting it as if it were current is not — this is a provenance failure (Principle 7),
  not merely a data-freshness one.
- **Hallucinated attributes** — any AI-assisted process asserting a fact (an ABV, a grape variety, a
  certification, a tasting note) that was not actually present in or reliably extractable from the
  evidence it was given. This is the AI Principles boundary stated as a failure mode: it must never
  happen, and if a model demonstrably does this, the extraction pipeline that allowed it — not just
  the individual output — needs to be reconsidered.
- **Quality quietly co-varying with price or marketing volume**, even as an emergent property of an
  otherwise well-intentioned model (e.g., a feature correlated with price sneaking in as a proxy).
  This is the circularity failure Principle 9 exists to prevent, and it is unacceptable *even when
  unintentional* — "the model learned it, we didn't design it that way" is not a defense under this
  philosophy.

---

## Versioning

**Established.** Every computed score is stamped with the model/methodology version that produced
it, at computation time — not inferred later from a timestamp. This is required for Principle 6
(reproducibility): "reproducible" only means something if you can identify *which* version's rules
are being reproduced.

**Recommendation.** The scoring *philosophy* (this document) should change rarely and deliberately —
it is closer to a constitution than a config file, and should require the same kind of explicit
justification a principle-level change to `platform-architecture.md` would. Scoring *models*
(the concrete formulas, weights, and methods that implement this philosophy) should be expected to
version far more often, as evidence sources are added, matching techniques improve, or a flaw like
the `rating_count_index` conflation is found and corrected. A model version change should never
require a philosophy change unless the model has drifted from a principle here — if that happens,
the model is wrong, not the philosophy.

**Recommendation — when to recompute.** A score should be recomputed whenever any of the following
occurs: new evidence arrives for its subject, an evidence source is deprecated or its reliability
class is revised, or the model version itself changes. A score should *not* silently go stale between
these triggers — if evidence hasn't refreshed in a long time, that should surface as a Confidence
signal (recency), not as an invisible gap.

**Established.** Historical scores are preserved, never overwritten in place — mirroring the
evidence ledger's append-only design in `platform-architecture.md` §05. A user (or engineer) should
always be able to ask "what did this wine score last quarter, and why was it different," and get a
real, reconstructable answer rather than a lost value. This is both a trust feature (users can see a
wine's trajectory) and an engineering safety net (a bad model version's damage is auditable and
reversible).

**Open question.** How long should full evidence and score history be retained, and at what
granularity? This is a genuine storage/cost/product tradeoff, not a principle this document can
settle — the principle is only that history must be preserved *in some form* for at least long
enough to explain "why did this change" for any score a user might currently be looking at.

---

## User trust

**The test case: "Why did this wine receive 91?"**

A user asking this should ideally be able to get, in escalating detail:

1. **A one-line answer** naming the dominant evidence — e.g., "primarily reflects a critic score and
   a large, consistent crowd rating" — never just "our algorithm calculated this."
2. **The evidence list**, each item with its source, its own value, and when it was retrieved.
3. **The confidence label and its reason** — e.g., "moderate confidence: based on two independent
   sources" — stated plainly enough that a user with no data-science background understands what
   it's hedging against.
4. **What the score is *not* claiming** — that it isn't personalized, that it isn't a taste
   guarantee, that it's an estimate that can and does change as evidence changes.
5. **A path to see the version and history**, for a user who wants to verify the score is
   reproducible and has been stable (or understand why it changed).

**Established.** If the platform cannot produce a real answer to all five of those — using the
system's actual stored evidence and version metadata, not a post-hoc justification — the score is
not ready to be shown as a bare number. It should instead be shown with its confidence state made
prominent, or not shown at all, until the explanation infrastructure catches up. Explainability is
not a feature layered on top of a finished score; it is a precondition for shipping one.

---

## Open questions

Collected from throughout the document, for visibility:

1. Should Quality ever be estimated for a Vintage with zero direct evidence, purely by inheritance
   from Producer/Wine track record? *(Quality)*
2. Should Confidence decay over time purely due to staleness, absent new contradicting evidence?
   *(Confidence, Versioning)*
3. How much of the explanation surface (the six required elements) should be shown by default versus
   behind an expansion, in the eventual UI? *(Explainability)*
4. Should the platform apply explicit counter-weighting to correct structural evidence imbalances
   (e.g., large international producers over-represented in crowd databases relative to small
   Icelandic-market imports), beyond simply not actively favoring them? *(Fairness)*
5. How long should full evidence and score history be retained, and at what granularity? *(Versioning)*

None of these block building a first version of the scoring engine — each can be resolved with a
narrower, reversible default and revisited once real evidence (usage data, cost data, or a concrete
edge case) makes the tradeoff legible. What they should not be resolved by is silent default inside
an implementation with no record that a choice was made.

---

*This document should be revisited only when a proposed scoring model cannot be built without
violating a principle here — at that point, the right question is whether the principle needs
refinement or the model needs to change. Absent that pressure, treat it as settled.*
