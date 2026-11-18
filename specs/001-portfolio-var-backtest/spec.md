# Feature Specification: Portfolio Risk and VaR Track Record for TraderX Accounts

**Feature Branch**: `001-portfolio-var-backtest`

**Created**: 2026-11-17

**Status**: Draft

**Input**: User description: "Feature number 001: Portfolio risk and VaR track record for TraderX accounts. A risk manager at a regulated firm needs, for each trading account, a one-day 99% Value-at-Risk figure and evidence that the model behind it can be trusted. Method fixed: filtered historical simulation with an EWMA volatility filter (lambda 0.94) and a 250-observation pool; positions held constant over the backtest window. Price history is synthetic from a fixed seed. Existing TraderX screens and APIs unchanged. Tests and an independent second implementation written by a different AI model from the spec only." (full text in `input.md` in this folder)

> **Note on detail level.** The constitution (Principle V) requires a second AI model to write the
> tests and an independent implementation **from this spec alone**, with expected values and
> tolerances recorded before any code exists. The calculation is therefore specified exactly in
> [Method Definition](#method-definition-normative). The formulas are requirements, not
> implementation choices. The spec still names no language, framework, endpoint or library.

## Clarifications

### Session 2026-11-18

- Q: Should the volatility filter be applied to the account's total daily dollar P&L, or to each security's price series separately before combining them? → A: Portfolio level. Filter the account's dollar P&L series at today's share counts (M2–M3). Per-security filtering is out of scope.
- Q: Besides looking up an account in TraderX, should the risk calculation also accept a position list supplied directly by the caller and return the same structured result? → A: Yes. A documented, read-only entry point takes a position list and returns the same result shape and outcomes as the account lookup, with provenance marking the positions as caller-supplied. It is not shown on the page (FR-020).
- Q: Should the synthetic price-history file be generated once and committed before the validator model starts writing tests, so that it counts as a fixed input like the spec? → A: Yes. A generator script and its output file, with a SHA-256 checksum, are committed under the feature folder before validation starts. Both implementations and all tests read that file, and any later change is a recorded amendment (FR-014).
- Q: Which date should the current VaR be labelled with: the as-of date of the data it uses, or the day it is a forecast for? → A: Both, as separate labelled fields: "data as of 2026-11-13 close" and "forecast for 2026-11-16" (FR-002).
- Amendment (H1, /speckit-analyze): SC-007 narrowed. Account and position lookups for the seeded accounts must return the same responses before and after, ignoring `updated`. The price lookup must return the same set of tickers and the same response shape; its values move, because price-publisher is a random walk. The "before" responses are captured into `specs/001-portfolio-var-backtest/validation/runs/baseline-before.json` before the baseline stack is stopped (SC-007).
- Amendment (H2, /speckit-analyze): in V2 and V4 the test fixes its own random seeds and writes them in the test file (V2: one seed per generated series, e.g. 0–399; V4: seed 20261117 for the perturbation factors). Only the pass band is pre-registered, not the individual draws (V2, V4).
- Amendment (H3, /speckit-analyze): V5 tolerance. LR and p-value agree with the table to within ±0.00005; the decision, direction and Basel zone match exactly (V5).
- Amendment (M2, /speckit-analyze): POSITIONS_UNAVAILABLE covers a failure of either TraderX lookup (account or position), and of the account list (edge cases, FR-011).
- Amendment (M3, /speckit-analyze): SC-008 compares the `current`, `track_record` and `verdict` blocks only; `provenance.positions_read_at` is excluded (SC-008).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See an account's current one-day 99% VaR (Priority: P1)

A risk manager picks a TraderX account and sees its one-day 99% VaR in dollars. Next to the
figure they see the positions it covers (security and signed quantity), the price used for each
position, each position's market value, and the account's net market value.

**Why this priority**: The VaR figure is the main deliverable. Without it, nothing else in the
feature means anything.

**Independent Test**: Request the risk figure for seeded account 22214 (MS +1000, IBM −100,
C −2000). Check that the positions and prices shown match the position list and the synthetic
closes on the as-of date. Check that an independent recomputation from the published price history
reproduces the dollar VaR within the agreement tolerance (SC-004).

**Acceptance Scenarios**:

1. **Given** account 22214 with seeded positions, **When** the risk manager requests its risk
   figure, **Then** they see a positive dollar VaR and the three positions with their signed
   quantities. Each position shows its price on the as-of date and its market value. The figure
   is labelled "data as of 2026-11-13 close" and "forecast for 2026-11-16".
2. **Given** an account ID that does not exist in TraderX, **When** its risk figure is requested,
   **Then** the result is an explicit "account not found" outcome with no VaR number, not zero and
   not blank.
3. **Given** an existing account with no open positions (e.g. 44044), **When** its risk figure is
   requested, **Then** the result is an explicit "no open positions — VaR not applicable" outcome
   with no VaR number.
4. **Given** an account holding a security with no synthetic price history, **When** its risk
   figure is requested, **Then** the result is an explicit "missing price history" outcome naming
   the security. No partial VaR is shown and no position is silently dropped.

---

### User Story 2 - See the backtest track record (Priority: P2)

For the same account, the risk manager sees one row for each of the 250 backtest days. Each row
shows the date, the VaR forecast made with data up to the previous close, the realised P&L of the
current positions on that day, and whether the day was a breach.

**Why this priority**: A VaR number without a track record cannot be trusted. Regulators judge the
model on its backtest.

**Independent Test**: Request the track record for account 22214. Check that it has exactly 250
rows and that the dates are consecutive synthetic business days ending on the as-of date. Check
that every row marked as a breach has realised P&L < −VaR and that no other row does. Rerun with
the history changed on or after a chosen day t and confirm the forecast for day t is unchanged
(FR-012).

**Acceptance Scenarios**:

1. **Given** account 22214, **When** the track record is requested, **Then** 250 rows are shown,
   ordered by date, and each has a forecast VaR, a realised P&L and a breach flag.
2. **Given** any row for day t, **When** any synthetic price on or after day t is changed, **Then**
   the VaR forecast for day t is unchanged to the last digit. The realised P&L for day t may change.

---

### User Story 3 - See a verdict on the model (Priority: P2)

Under the track record, the risk manager sees a verdict:

- the observed breach count, set against both the nominal expectation (2.5) and the finite-sample
  expectation (3.5);
- the breach rate;
- the Kupiec unconditional coverage test (statistic, p-value, and reject or do not reject at 5%);
- the Basel traffic-light zone.

**Why this priority**: This turns 250 rows into the question a risk manager has to answer: can this
model be used?

**Independent Test**: For a given breach count, check that the verdict's Kupiec statistic, p-value
and zone match the reference table in [Verification Expectations](#verification-expectations-pre-registered).

**Acceptance Scenarios**:

1. **Given** a track record with x breaches, **When** the verdict is shown, **Then** it shows x,
   x/250, "nominal expectation 2.5", "finite-sample expectation 3.5", the Kupiec LR statistic and
   p-value, the reject or do-not-reject decision at 5%, and the Basel zone (green 0–4, amber 5–9,
   red ≥10).
2. **Given** a track record with 0 breaches, **When** the verdict is shown, **Then** Kupiec rejects
   (LR ≈ 5.03), and the verdict says the rejection comes from too few breaches (a model that is
   too conservative), not too many.
3. **Given** any verdict, **Then** it includes a fixed note: a correct implementation reaches the
   amber zone or worse roughly a quarter of the time, so amber alone does not prove the model
   wrong.

---

### User Story 4 - See what every number is based on (Priority: P3)

Every VaR figure, track record and verdict carries a provenance label. The label says that the
price history is synthetic, and gives the seed, the model settings (method name, λ, pool size,
warm-up length, confidence level, horizon, quantile rule), the as-of date and the position source
(the TraderX read time, or "caller-supplied").

**Why this priority**: The constitution (Project Constraints, Principle IV) requires honest
labelling. An auditor reading any single output must be able to tell that it is not real market
risk.

**Independent Test**: Request each result type (current VaR, track record, verdict, and each error
outcome) and confirm that every one carries the full provenance label with the word "synthetic".

**Acceptance Scenarios**:

1. **Given** any successful risk result, **Then** it is labelled "SYNTHETIC price history" and shows
   seed 20261117, method "filtered historical simulation, EWMA λ=0.94", pool 250, warm-up 100,
   confidence 99%, horizon 1 day, quantile rule "linear interpolation, position (n−1)p", and
   as-of date 2026-11-13.
2. **Given** the new risk page, **When** it is viewed, **Then** the synthetic-data label is visible
   without scrolling.

---

### Edge Cases

- **Unknown account**: explicit not-found outcome (FR-008). Never zero or an empty figure.
- **Account with no open positions** (the seeded accounts 11413, 42422, 62654, 10031 and 44044 have
  none): explicit "no open positions" outcome with no VaR number (FR-009).
- **Position with zero quantity**: ignored, because a flat position carries no risk. If every
  position is zero, the result is the same as for no positions.
- **Security without synthetic history** (TraderX accepts trades in any of ~500 reference-data
  tickers, but history covers only the 20 priced tickers): explicit "missing price history" outcome
  listing the affected securities (FR-010).
- **Positions change between requests** (a trade is booked): the next request reflects the new
  positions. The backtest re-applies the new constant positions over the whole window. The
  provenance shows when the positions were read.
- **Zero filtered volatility** (all P&L in the warm-up is zero, possible only for degenerate
  inputs): explicit "VaR not computable: zero volatility" outcome, never a division error or NaN.
- **Interpolated quantile ≥ 0** (possible only with tiny or adversarial pools such as the hand
  example's variants): the VaR is reported as computed, even if zero or negative, and is not
  floored. The hand-checkable example defines the arithmetic.
- **P&L exactly equal to −VaR**: not a breach (breach requires strict inequality on unrounded
  values).
- **TraderX unavailable** (the position service, the account service, or the account list
  cannot be reached): explicit "positions unavailable" outcome (`POSITIONS_UNAVAILABLE`), never a
  VaR computed on an empty or stale position list. The same outcome covers a failure of either
  TraderX lookup (account or position) and of the account list.

## Requirements *(mandatory)*

### Functional Requirements

**Risk figure**

- **FR-001**: The system MUST give a one-day 99% VaR in US dollars for a chosen TraderX account,
  computed exactly as defined in [Method Definition](#method-definition-normative).
- **FR-002**: Every VaR result MUST show the positions it covers (security, signed quantity), the
  price used for each (the synthetic close on the as-of date), each position's market value, and
  the account's net market value. It MUST carry two separately labelled dates: "data as of" the
  as-of date close (2026-11-13), and "forecast for" the next synthetic business day after it
  (2026-11-16), the day N+1 in M5. Each backtest row is dated by the day it forecasts (day t).
- **FR-003**: Positions MUST be the account's current positions as recorded by TraderX, read without
  changing them. Prices MUST come from the synthetic history (Method Definition M1), not from the
  live price stream.

**Track record and verdict**

- **FR-004**: The system MUST give a backtest track record of exactly 250 rows, one for each
  synthetic business day in the backtest window ending on the as-of date. Each row MUST hold the
  date, the forecast VaR for that day, the realised P&L for that day, and a breach flag.
- **FR-005**: A day MUST be flagged as a breach if and only if realised P&L < −VaR forecast,
  compared on unrounded values.
- **FR-006**: The system MUST give a verdict holding: the breach count; the breach rate (count/250);
  the nominal expected count 2.5; the finite-sample expected count 3.5 (exact value 3.476); the
  Kupiec LR statistic, its p-value, and reject or do-not-reject at the 5% level; the direction of
  any rejection (too many or too few breaches); and the Basel traffic-light zone.
- **FR-007**: The Kupiec test MUST use the nominal level p = 0.01 as its null, with the formula in
  M6. The Basel zone MUST use the 250-observation thresholds: green 0–4, amber 5–9, red ≥10
  (Basel Framework, MAR32.9 Table 1 and MAR99.17 Table 2, version effective 1 January 2023, read
  on 2026-11-18). The zone names follow that text: green, amber, red. The boundaries are the same
  as in the original January 1996 backtesting framework, which called the middle zone yellow.

**Error outcomes**

- **FR-008**: An account ID that does not exist in TraderX MUST return a distinct "account not
  found" outcome with no VaR, track record or verdict.
- **FR-009**: An existing account with no positions of non-zero quantity MUST return a distinct "no
  open positions" outcome with no VaR number.
- **FR-010**: An account holding any security without synthetic history MUST return a distinct
  "missing price history" outcome naming every such security. Partial VaR is not allowed.
- **FR-011**: Outcomes FR-008, FR-009 and FR-010, the zero-volatility outcome, and the
  positions-unavailable outcome MUST each be distinguishable by machine and by a person reading the
  page, from each other and from a successful result. The positions-unavailable outcome
  (`POSITIONS_UNAVAILABLE`) covers a failure of either TraderX lookup, account or position, and
  a failure of the account list.

**Integrity**

- **FR-012 (no look-ahead)**: The forecast VaR for day t MUST depend only on closes dated before t,
  and on the positions. Changing any close on or after day t MUST leave the forecast for day t
  bit-for-bit unchanged.
- **FR-013 (determinism)**: Given the same positions and the same synthetic history, every output
  number MUST be identical across runs and restarts.
- **FR-014 (synthetic data)**: The synthetic price history MUST be generated from the fixed seed
  20261117 by the documented process in M1. The generator script, its output data file and the
  file's SHA-256 checksum MUST be committed under this feature folder before the validator model
  starts. The file is a fixed input owned by neither the implementing nor the validating side, and
  it is the authoritative input for both implementations and all tests. The service MUST read this
  file and MUST NOT regenerate or modify it. Any later change to the file is an amendment recorded
  in the spec with its new checksum. The data MUST be labelled synthetic wherever it is shown or
  served.
- **FR-015 (provenance)**: Every result, errors included, MUST carry the provenance label: synthetic
  price history, seed, method name, λ, pool size, warm-up length, confidence level, horizon,
  quantile rule, as-of date, and the position source: either "TraderX account" with the time the
  positions were read, or "caller-supplied" (FR-020).
- **FR-016 (honest verdict context)**: The verdict MUST include the fixed note from User Story 3,
  scenario 3.

**Presentation and non-interference**

- **FR-017**: The risk manager MUST be able to pick any TraderX account and view FR-002, FR-004 and
  FR-006 on one new read-only page outside the existing TraderX front end. The synthetic label
  (FR-015) must be visible without scrolling.
- **FR-018**: The existing TraderX screens, APIs and events MUST NOT change. The only baseline
  edits allowed are deployment wiring, each listed in the plan (constitution, Principle II).
- **FR-019**: Results MUST be readable by machine in a documented structured form, so the
  independent implementation and the tests can compare numbers without scraping the page.
- **FR-020 (caller-supplied positions)**: The structured interface MUST also accept a position list
  (security, signed quantity) supplied directly by the caller, with no account lookup. It MUST
  return the same current VaR, track record and verdict, and the same outcomes FR-009, FR-010 and
  zero volatility, as an account with those positions would. Provenance MUST mark the positions as
  "caller-supplied". This entry point is read-only, changes nothing in TraderX, and is not shown on
  the page.

### Method Definition *(normative)*

Notation: closes are indexed by synthetic business day s = 0 … N. Position quantities qᵢ are
signed share counts: long > 0, short < 0. Parameters for this feature: λ = 0.94, pool size
n = 250, warm-up W = 100, p = 0.01. Backtest length B = 250, so N = W + n + B = 600 P&L days and
601 closes. The calculation MUST take λ, n, W and p as parameters, so the hand-checkable example
can use a small pool and warm-up.

- **M1 — Synthetic history.**
  - **Calendar:** 601 business days (Monday–Friday, no holidays, labelled as a synthetic calendar)
    ending on the as-of date 2026-11-13 (s = 600).
  - **Tickers:** the 20 tickers in the TraderX price snapshot.
  - **Returns:** daily log returns from a one-factor Gaussian model. The market factor follows
    GARCH(1,1) with α = 0.08, β = 0.90 and long-run daily volatility 1.0%, so ω = (1 − α − β) ·
    0.01² = 2 × 10⁻⁶. The process starts at the long-run variance (σ₀² = 10⁻⁴) with no burn-in.
    Every ticker's factor loading is 1.0. Idiosyncratic shocks are i.i.d. normal with daily
    volatility 1.5%. All draws come from seed 20261117.
  - **Scaling:** each ticker's path is scaled so that its close on the as-of date equals that
    ticker's `closePrice` in the TraderX price snapshot.
  - **Publication:** the generated closes are published as data (FR-014). The data, not the
    generator, is authoritative.
    - File: `specs/001-portfolio-var-backtest/data/synthetic_prices_seed20261117.csv`. It is wide
      format: a `date` column, then one column per ticker in snapshot order. It has 601 rows from
      2024-07-26 to 2026-11-13, with closes at 4 decimal places. The rounded values are the
      prices.
    - SHA-256: `9ea2eab18bc0bf108fffb90245fd7f51a07e0fa16e52d49564e20c50e0718ce3` (also in
      `data/SHA256SUMS`).
    - Generator: `data/generate_synthetic_prices.py`. It starts the factor variance at its
      long-run value (h₁ = 0.01²), draws u[600] and then e[600×20] from
      `default_rng(20261117)`, and has zero drift. Run with `--check` it rebuilds the file in
      memory and compares it with the committed one. Generation parameters are in
      `data/synthetic_prices_seed20261117.meta.json`.
  - **Precision:** the values as written in the file are the inputs; no implementation uses
    higher-precision values from the generator.
  - **Anchor check:** the generator MUST stop with an error unless every as-of close in the file
    equals that ticker's snapshot `closePrice`.
- **M2 — Portfolio P&L.** For s = 1 … N: xₛ = Σᵢ qᵢ · (Pᵢ,ₛ − Pᵢ,ₛ₋₁). Dollar P&L uses today's
  constant positions. There is no percentage return on net value, which would not be defined for
  long/short accounts.
- **M3 — EWMA filter (zero mean, lagged).**
  - **Seed:** σ²_{W+1} = (1/W) · Σ_{s=1..W} xₛ².
  - **Recursion:** for s ≥ W+1, σ²_{s+1} = λ·σ²ₛ + (1−λ)·xₛ².
  - **Timing:** σₛ uses only P&L up to day s−1.
  - **Residuals:** zₛ = xₛ / σₛ for s = W+1 … N.
- **M4 — Quantile.** For a pool z₁ … zₙ, sort ascending to z₍₁₎ ≤ … ≤ z₍ₙ₎ and set h = (n−1)·p,
  k = ⌊h⌋ and w = h − k. Then Q = z₍ₖ₊₁₎ + w·(z₍ₖ₊₂₎ − z₍ₖ₊₁₎), using 1-based order statistics.
  When k+2 > n, Q = z₍ₖ₊₁₎. For n = 250 and p = 0.01: h = 2.49, so
  Q = z₍₃₎ + 0.49·(z₍₄₎ − z₍₃₎).
- **M5 — VaR forecast for day t.** The pool is the n residuals z_{t−n} … z_{t−1}, and
  VaRₜ = −σₜ · Q(pool), in dollars. Backtest days are t = N−B+1 … N (that is, 351 … 600). The
  **current VaR** is the forecast for day N+1, using σ_{N+1} and residuals z_{N−n+1} … z_N. It is
  the next-day risk of today's positions at the as-of-date closes.
- **M6 — Kupiec test.** With T = 250, x breaches, and p = 0.01:
  LR = −2·[ (T−x)·ln(1−p) + x·ln p − (T−x)·ln(1−x/T) − x·ln(x/T) ], with 0·ln 0 = 0.
  p-value = 1 − F_{χ²(1)}(LR). Reject at 5% when LR > 3.8415. The direction is "too many" if
  x > 2.5 and "too few" if x < 2.5.
- **M7 — Finite-sample expectation.** A new observation falls below the M4 quantile of n
  exchangeable continuous draws with probability ≈ (k+1+w)/(n+1) = 3.49/251 = 1.3904%. Over 250
  days that is 3.476 breaches, shown as 3.5. The nominal level is 1.00%, which is 2.5 breaches.

### Key Entities

- **Account**: an existing TraderX account (ID, display name). Read only.
- **Position**: a security and signed quantity, either read from an existing TraderX account (read
  only) or supplied by the caller (FR-020). Held constant over the backtest.
- **Synthetic price history**: 601 daily closes for each of 20 tickers on a synthetic business-day
  calendar ending 2026-11-13. It is generated from seed 20261117 and labelled synthetic.
- **Model settings**: the method name, λ, n, W, p, horizon and quantile rule. These are fixed for
  this feature.
- **Risk result**: the current VaR, the positions and prices used, net market value, provenance and
  outcome status.
- **Backtest row**: date, forecast VaR, realised P&L and breach flag.
- **Verdict**: breach count, rate, nominal and finite-sample expectations, Kupiec LR, p-value,
  decision and direction, Basel zone, and the fixed explanatory note.
- **Provenance label**: the fields listed in FR-015, attached to every result.

## Verification Expectations *(pre-registered)*

These values were written before any code, as Principle V requires. If a result misses one, the
miss is recorded with its cause in `disputes.md` or the plan. Tolerances are not widened.

**V1 — Hand-checkable example (paper arithmetic).** One security, q = 10 shares, λ = 0.94, W = 2,
n = 5, p = 0.01. Closes C₀ … C₈ = 100, 101, 99, 100, 97, 98, 99, 96, 93.

| s | xₛ | σ²ₛ | σₛ | zₛ |
|---|----|-----|----|----|
| 1 | +10 | – | – | – |
| 2 | −20 | – | – | – |
| 3 | +10 | 250.000000 | 15.811388 | +0.632456 |
| 4 | −30 | 241.000000 | 15.524175 | −1.932470 |
| 5 | +10 | 280.540000 | 16.749328 | +0.597039 |
| 6 | +10 | 269.707600 | 16.422777 | +0.608910 |
| 7 | −30 | 259.525144 | 16.109784 | −1.862222 |
| 8 | −30 | 297.953635 | 17.261334 | (realised) |

- The pool is z₃ … z₇. h = 0.04, so Q = −1.932470 + 0.04 × (−1.862222 + 1.932470) = −1.929660.
- **VaR₈ = 17.261334 × 1.929660 = $33.3085**, which must be reproduced within $0.0001.
- The realised x₈ = −30 > −33.31, so day 8 is **not a breach**.
- **Variant:** if C₈ = 92 instead, then x₈ = −40, day 8 **is a breach**, and VaR₈ is still
  $33.3085, because a change on day t leaves the forecast for t unchanged.

**V2 — Known-answer coverage test.**

- **Generator:** an EWMA-consistent generator, where the true volatility is exactly the M3
  recursion. It sets xₛ = zₛ for s ≤ W and xₛ = σₛ·zₛ afterwards, with zₛ i.i.d. N(0,1). This
  makes the true standardized residuals i.i.d. by construction.
- **Run:** 400 independent series, each with W = 100, n = 250 and B = 250, for 100,000 forecasts in
  total.
- **Seeds:** the test fixes its own random seeds and writes them in the test file, one seed per
  generated series (for example 0–399). Only the pass band below is pre-registered, not the
  individual draws.
- **Pass:** the pooled breach rate lies in **[1.24%, 1.54%]**. This band is about 1.39% ± 5
  standard errors; the empirical standard error is about 0.031 percentage points.
- **The band excludes 1.00%.** An implementation that achieves exactly nominal coverage under this
  quantile rule is evidence of an error, such as a different quantile convention or look-ahead in σ.
- **Pre-study:** a simulation run while writing this spec gave 1.392%. A constant-volatility i.i.d.
  normal generator gave 1.357%, which is also inside the band.
- **Reproduction:** an independent rerun on 2026-11-17 with five further seeds gave 1.34%–1.42%
  for the EWMA-consistent generator and 1.35%–1.37% for the i.i.d. generator, with a standard
  error of 0.030–0.033 percentage points. The script is committed as
  `specs/001-portfolio-var-backtest/validation/prestudy_coverage.py`.

**V3 — Independent second implementation.** It is written by a different AI model from this spec
only. On the published synthetic history and the seeded accounts 22214 and 52355:

- every current VaR and every backtest forecast agrees within **$0.01**;
- breach flags are identical;
- verdict fields are identical, apart from floating-point formatting of LR and the p-value, which
  must agree within 1e-6.

**V4 — No look-ahead perturbation.** For at least 3 days t in the backtest window, including the
first (351) and the last (600), multiply every close on or after t by a random factor in
[0.5, 1.5]. The forecast VaRₜ must be bit-for-bit identical before and after. The test fixes the
seed for the perturbation factors at 20261117 and writes it in the test file. Only the pass
criterion is pre-registered, not the individual draws.

**V5 — Kupiec and Basel reference values** (T = 250, p = 0.01):

| Breaches | LR | p-value | Kupiec 5% | Basel zone |
|---|---|---|---|---|
| 0 | 5.0252 | 0.0250 | reject (too few) | green |
| 1 | 1.1765 | 0.2781 | do not reject | green |
| 2 | 0.1084 | 0.7419 | do not reject | green |
| 3 | 0.0949 | 0.7580 | do not reject | green |
| 4 | 0.7691 | 0.3805 | do not reject | green |
| 5 | 1.9568 | 0.1619 | do not reject | amber |
| 6 | 3.5554 | 0.0594 | do not reject | amber |
| 7 | 5.4970 | 0.0190 | reject (too many) | amber |
| 10 | 12.9555 | 0.0003 | reject (too many) | red |

**Tolerance:** LR and p-value agree with the table to within ±0.00005; the decision, direction and
Basel zone match exactly.

**V6 — Outcomes.** The following each return their distinct outcome with full provenance and no
VaR number:

- account 99999 (does not exist);
- account 44044 (no positions);
- a position list that includes a security outside the 20 priced tickers (missing history). No
  seeded account holds one, so this case is checked through the caller-supplied entry point
  (FR-020), not by booking a trade in TraderX.
- a caller-supplied position list identical to account 22214's seeded positions returns the same
  VaR, track record and verdict as account 22214, with provenance "caller-supplied".

**Not pre-registered on purpose:** the Basel zone and breach count for the seeded demo accounts.
At a 1.39% true rate, a correct model reaches amber or worse roughly a quarter of the time (27%
for independent days; 22%–28% in the pre-study simulation), so a single 250-day outcome is not a
pass or fail criterion. Whatever it is, it is reported as observed. For comparison, the Basel
text puts this chance at 10.8% for a model whose true rate is exactly 1% (MAR99 Table 1, notes:
type 1 error for a cut-off of five or more exceptions). The gap comes from the finite-sample
coverage in M7, not from a flaw in the model, and the result view says so next to the zone.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A risk manager can go from opening the risk page to reading an account's VaR, its
  positions and prices, and its verdict in under 1 minute, without leaving the page.
- **SC-002**: Each result (current VaR, track record and verdict) for any seeded account appears in
  under 5 seconds on a single workstation.
- **SC-003**: The V1 hand example is reproduced to $0.0001, and the V2 known-answer breach rate falls
  inside [1.24%, 1.54%].
- **SC-004**: The two independent implementations agree on 100% of figures within $0.01, and their
  breach flags match on all 500 account-days (2 accounts × 250).
- **SC-005**: 100% of perturbation checks (V4) leave the forecast unchanged.
- **SC-006**: 100% of result types, error outcomes included, carry the synthetic label and full
  provenance. A reviewer finds no number shown without its basis.
- **SC-007**: The existing TraderX account and position lookups for the seeded accounts return
  the same responses before and after the feature, ignoring the `updated` field. The price lookup
  returns the same set of tickers and the same response shape; its values move, because
  price-publisher is a random walk. The "before" responses are captured into
  `specs/001-portfolio-var-backtest/validation/runs/baseline-before.json` before the baseline stack
  is stopped. The diff against the baseline commit shows only new files plus the wiring edits
  listed in the plan.
- **SC-008**: Two runs from a clean start produce byte-identical numeric results for the same
  positions. The comparison covers the `current`, `track_record` and `verdict` blocks only;
  `provenance.positions_read_at` is excluded.

## Assumptions

- **Filtering level**: Filtering is applied to the portfolio's dollar P&L series (M2–M3), not to each
  security separately. Both are filtered historical simulation. The portfolio-level form is
  hand-checkable, works for long/short accounts, and keeps the finite-sample coverage argument
  (M7) a close approximation, because a breach is then the same event as a residual falling
  below the pool quantile. Per-security filtering would give different numbers and is out of scope. *(Confirmed
  by the author, Clarifications 2026-11-18.)*
- **Synthetic generator and seed**: Seed 20261117, the one-factor GARCH(1,1)/Gaussian model in M1,
  and the as-of date 2026-11-13 are defaults chosen for this spec. The published data file, not the
  generator code, is authoritative, because random-number streams differ across languages. The
  file is generated and committed at the spec stage, before validation (FR-014). The generator is
  written by Claude (the implementing model), reviewed and run by the author, and committed before
  the validator model starts. It follows M1 exactly, so it gives the implementing side no choice
  over the test input. *(Seed, model and as-of date are defaults; the author may override them
  before the file is committed.)*
- **"Current price"**: This is the synthetic close on the as-of date, which by construction equals
  the TraderX price snapshot close. It is not the live ticking price. This keeps results
  deterministic (constitution Principle III) and keeps intraday recalculation out of scope.
- **Kupiec null**: The test uses the nominal 1% (the regulatory convention), not the finite-sample
  1.39%. The finite-sample value is shown next to it as context, as required.
- **Warm-up**: W = 100 P&L days seed the EWMA. That data is used before every forecast, so it adds
  no look-ahead. 0.94¹⁰⁰ ≈ 0.002, so the initial seed has negligible weight once the pool starts.
- **Positions**: Positions are read from the existing TraderX position records at request time, and
  quantity-zero rows are ignored. Positions are held constant over the backtest window, as the
  method requires. That window describes today's book under past prices, not historical books.
  This matches the hypothetical P&L the Basel text asks banks to be able to backtest against,
  computed as if "end-of-day positions [were] to remain unchanged" (MAR99.6). Backtesting
  against actual P&L, which includes intraday trading and fees, is out of scope.
- **Access**: The page and data are for a single trusted local user, and the stack binds to
  127.0.0.1. This feature adds no authentication or entitlements.
- **Display**: Dollar amounts are shown to the cent. All comparisons and the agreement tolerances
  use unrounded values.
- **Out of scope**: real market data, expected shortfall, multi-day horizons, other confidence
  levels, intraday recalculation, historical position reconstruction, changes to the Angular front
  end, and any change to existing TraderX APIs or events.
- **Dependencies**: the existing TraderX account and position records (read only), the 20-ticker
  price snapshot (used only to anchor the last synthetic close), and the existing deployment
  wiring, edited only as listed in the plan.
