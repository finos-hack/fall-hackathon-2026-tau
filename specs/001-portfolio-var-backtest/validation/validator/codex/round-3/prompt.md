# System instructions

You are the independent validator for feature 001 of this repository. Under its constitution
(Principle V), a different AI model writes the implementation. You write the tests, and an
independent second implementation, working only from the inputs below. You have not seen the
implementation, and you must not guess at it.

## Inputs

The user message ends with these files, each between BEGIN and END markers:

1. `.specify/memory/constitution.md`: the project constitution.
2. `specs/001-portfolio-var-backtest/spec.md`: the feature specification, including the
   Verification Expectations V1–V6 and Success Criteria SC-001–SC-008.
3. `specs/001-portfolio-var-backtest/contracts/calculation-api.md`: the Python calculation
   contract.
4. `specs/001-portfolio-var-backtest/contracts/http-api.md`: the HTTP contract.
5. `specs/001-portfolio-var-backtest/contracts/data-model.md`: the entities and fields.
6. `specs/001-portfolio-var-backtest/contracts/test-harness.md`: paths, environment variables,
   commands, tiers and file formats.
7. `specs/001-portfolio-var-backtest/data/synthetic_prices_seed20261117.meta.json` and
   `SHA256SUMS`: the frozen data's metadata and checksums.
8. A sample of `specs/001-portfolio-var-backtest/data/synthetic_prices_seed20261117.csv`: the
   header, the first 3 rows and the last 3 rows. The tests read the full file from its path.
9. (round 3 only) Every `tests/oracle/*.py` file: round 2's accepted output, the independent
   implementation and its tests.

Use nothing else. Where these inputs do not settle a question, do not invent an answer. Leave
that case out, and list it under "Open questions" at the end of your answer.

## Rules for the tests

- Python 3.9 or later, pytest, and the standard library only. Tests must run offline.
- Every expected value and tolerance must come from `spec.md` or a contract. Above each
  assertion, add a comment naming the section it comes from (for example `# spec V5`).
- Any random numbers come from seeds fixed in the test file, as `spec.md` V2 and V4 require.
- Do not weaken a pre-registered tolerance. Do not assert anything the spec says is reported "as
  observed".
- Write files only under the `tests/` folder named in the round instructions.
- Every file name must be unique across `tests/`. Use `test_unit_*.py` in `tests/unit/`,
  `test_oracle_*.py` and `oracle_*.py` in `tests/oracle/`, and `test_integration_*.py` in
  `tests/integration/`. A `conftest.py`, if needed, is allowed once per folder. Do not use
  subfolders.

## Output format

Return every file as one fenced code block. The opening fence is three backticks followed
immediately by `python file=` and the file's path from the repository root, for example
`tests/unit/test_unit_example.py`. The block contains the complete file content and nothing else. Use
one block per file and give each path once. After the last file, add a short section headed
"Open questions" (plain text, not in a code block). Write nothing else outside the code blocks.


# Task

# Round 3: integration tests (tier 2, the running stack)

**Folder**: `tests/integration/`. Write files only there.

**Scope**: tests of the HTTP contract (`contracts/http-api.md`) against the running service.
Base URLs come from the environment variables in `contracts/test-harness.md`. Cover:

- **spec V6**: the outcome cases.
- **FR-011 and the outcome precedence**: every outcome and its HTTP status, and the precedence
  order in `contracts/http-api.md`.
- **FR-020**: caller-supplied positions against the account path for the same positions.
- **SC-006 and FR-015**: provenance on every response type, error outcomes included.
- **SC-007**: the baseline comparison against the file named in `contracts/test-harness.md`
  § Baseline responses, with the comparison rules in SC-007.
- **SC-008**: the determinism comparison as stated in SC-008.
- **V3 and SC-004 over HTTP**: compare the service's results with the independent implementation
  in `tests/oracle/`. Its files are attached as input 9. `tests/` has no `__init__.py`, so load the
  oracle module from its file path with `importlib`; do not use a package import.
- **SC-002**: the response-time criterion.

**Not in this round**: the calculation-contract unit tests (round 1), and writing or changing
anything in `tests/oracle/` (round 2).

**Inputs**: the files listed in the system message, attached below.

**Output format**: as described in the system message.


# Inputs

===== BEGIN FILE: .specify/memory/constitution.md =====
# TraderX Portfolio Risk (Hackathon Tau) Constitution

## Core Principles

### I. Spec-First, Feature-Scoped
Every change to code, configuration, or tests MUST trace to a numbered feature pack under
`specs/NNN-feature-name/` (`spec.md`, `plan.md`, `tasks.md`). Work not listed in the active
`tasks.md` MUST NOT be implemented. The human author writes and approves the spec; AI tools
MAY draft, review, and implement, but MUST NOT begin implementation before the author approves
`tasks.md`.

### II. Additive Delta on an Unmodified Base
The TraderX state 008 snapshot imported in commit `fbdfb38` (finos/traderX@d6e7fe4) is the
baseline. New behaviour MUST be delivered as new components (services, pages, tests). Edits to
baseline files are limited to wiring (compose, ingress, monitoring config), and each such edit
MUST be listed in the feature's `plan.md` with its reason. Existing 008 APIs and events MUST keep
their current contracts.
Rationale: `git diff fbdfb38` must show exactly what this project added.

### III. Deterministic, Offline Reproducible
Given the same inputs and seed, every computation MUST produce identical output. Any synthetic
data MUST be generated from a fixed, documented seed. The full stack and all tests MUST run on a
single workstation with no network access beyond pulling container images.

### IV. Evidence-Gated Completion
A requirement is complete only when a traceability table maps it FR → code location → test, and
that test passes. Claims in the README or demo MUST point to a test or a recorded output. A claim
without runnable evidence MUST be removed or labelled as not yet verified.

### V. Verifiable Without Trusting the Author
Risk numbers MUST be checked by at least three independent means:
(a) a hand-checkable example small enough to compute on paper;
(b) a known-answer test on synthetic data whose true distribution is known;
(c) an independent second implementation of the core calculation.
Expected values and tolerances MUST be written in the spec before the code runs, and MUST
account for finite-sample properties of the estimator (for example, the order-statistic
coverage of an empirical quantile), not only the nominal level. When a result misses its
expectation, the miss MUST be recorded with its cause; tolerances MUST NOT be widened after the
fact to make a test pass.
Tests and the independent implementation in (c) MUST be authored by a different AI model
than the one that writes the implementation, working only from the constitution, the spec,
and the contracts, never from the implementation source. The implementing side MUST NOT
edit files under `tests/`; a suspected test error is recorded in `disputes.md` and decided by
the human author. The prompt given to the validator model and its raw output MUST be committed.

### VI. No Look-Ahead
A risk figure for date t MUST use only data observable before t. Each backtest MUST include a
test that perturbs data on or after t and shows the figure for t does not change.

## Project Constraints

- Deadline: submission by 2026-11-18 end of day ET; scope MUST fit the remaining time. One new
  service plus a static page; no rebuild of the Angular front end.
- Access: the stack binds to `127.0.0.1` only (local override file).
- Honest labelling: synthetic data, simplifications, and approximations MUST be labelled as such
  in the UI, API responses, and README.
- Data and licence hygiene: vendored or copied code MUST record its source, commit, and licence;
  no proprietary or licence-restricted data is committed.
- Every commit MUST carry a DCO `Signed-off-by` from the human author; AI tools MUST NOT run
  `git config`, set author identity, force-push, or rewrite pushed history.

## Development Workflow and Quality Gates

1. `/speckit-specify` → `/speckit-clarify`: no open `[NEEDS CLARIFICATION]` markers remain.
2. `/speckit-plan`: plan lists baseline files touched (Principle II) and the verification design
   (Principle V).
3. `/speckit-tasks` → `/speckit-analyze`: every FR maps to at least one task and one test.
4. Author approves `tasks.md`. Validator-authored tests are committed first and MUST fail
   against an empty implementation; only then `/speckit-implement`.
5. Gate before submission: all tests pass, the traceability table is complete, and the stack
   starts from a clean checkout with the documented command.

## Governance

This constitution overrides conflicting conventions in this repository. Only the human author
amends it. Each amendment updates the version line and records the change in the commit message.
Versioning: MAJOR for removing or redefining a principle, MINOR for adding a principle or
section, PATCH for wording. `/speckit-analyze` and review before each commit check compliance;
any deviation MUST be written down in `plan.md` with its reason.

**Version**: 1.1.0 | **Ratified**: 2026-11-17 | **Last Amended**: 2026-11-17

===== END FILE: .specify/memory/constitution.md =====

===== BEGIN FILE: specs/001-portfolio-var-backtest/spec.md =====
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
- Amendment (round 2 review): account 52355's seeded position is BAC −2400 (`traderx/database/initialSchema.sql`; confirmed in `validation/runs/baseline-before.json`). It was missing from this spec, so the round 2 validator had no source for it (V3).

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
only. On the published synthetic history and the seeded accounts 22214 (C −2000, IBM −100,
MS +1000) and 52355 (BAC −2400):

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

===== END FILE: specs/001-portfolio-var-backtest/spec.md =====

===== BEGIN FILE: specs/001-portfolio-var-backtest/contracts/calculation-api.md =====
# Contract: Calculation API (Python, pure functions)

This is the contract the validator's offline tests call: V1, V2, V4, V5, and the core of V3. Every
function is pure. None reads files, the network or the clock, so tests can pass their own prices,
P&L series and parameters (spec M1–M7).

- **Module**: `risk_service.core`
- **Import**: run from the repository root with `PYTHONPATH=risk-service`, e.g.
  `PYTHONPATH=risk-service python3 -m pytest tests/`.
- **Python**: 3.9 or later; standard library only.

## Indexing convention (applies to everything below)

- **Inputs are plain lists.** A closes list holds C₀ … C_N, so `closes[s]` is the close on day s.
  A P&L list holds x₁ … x_N, so `pnl[s-1]` is xₛ.
- **Outputs are keyed by the spec's day number s or t.** Keys use the spec's 1-based day numbers
  as `dict[int, float]`, so test code can use the spec formulas directly.
- **Series length sets everything.** N = `len(pnl)`. Backtest days are t = W+n+1 … N, so
  B = N − W − n, which may be 0. The current forecast is t = N+1. The service itself always has
  N = 600, B = 250.

## Types

```python
@dataclass(frozen=True)
class Params:
    lam: float = 0.94
    pool: int = 250      # n
    warmup: int = 100    # W
    p: float = 0.01

class ZeroVolatilityError(ValueError): ...      # sigma^2_{W+1} == 0
class InsufficientHistoryError(ValueError): ... # len(pnl) < W + n

@dataclass(frozen=True)
class BacktestRow:
    t: int
    forecast_var: float
    pnl: float
    breach: bool          # pnl < -forecast_var, unrounded

@dataclass(frozen=True)
class Backtest:
    rows: list            # list[BacktestRow], t ascending, length N - W - n
    current_var: float    # forecast for day N+1

@dataclass(frozen=True)
class Kupiec:
    lr: float
    p_value: float
    reject: bool          # lr > 3.841458820694124
    direction: Optional[str]  # "too_many" | "too_few" when reject, else None
```

## Functions

| Function | Returns | Spec |
|---|---|---|
| `pnl_series(closes: Mapping[str, Sequence[float]], positions: Mapping[str, float]) -> list[float]` | x₁ … x_N, where xₛ = Σᵢ qᵢ·(Pᵢ,ₛ − Pᵢ,ₛ₋₁), summed in ascending ticker order. All close lists must have equal length N+1 ≥ 2. Every position ticker must be in `closes` (otherwise `KeyError`). | M2 |
| `ewma_sigmas(pnl, params) -> dict[int, float]` | σₛ for s = W+1 … N+1. Raises `ZeroVolatilityError` if σ²_{W+1} = 0. | M3 |
| `residuals(pnl, params) -> dict[int, float]` | zₛ = xₛ/σₛ for s = W+1 … N | M3 |
| `interp_quantile(values: Sequence[float], p: float) -> float` | the M4 quantile of the values (unsorted input allowed) | M4 |
| `var_forecasts(pnl, params) -> dict[int, float]` | VaRₜ = −σₜ·Q(z_{t−n} … z_{t−1}) for t = W+n+1 … N+1. Raises `InsufficientHistoryError` if N < W+n. | M5 |
| `backtest(pnl, params) -> Backtest` | rows for t = W+n+1 … N, plus current_var | M5, FR-005 |
| `kupiec(breaches: int, T: int, p: float) -> Kupiec` | the M6 LR (0·ln 0 = 0) and p-value erfc(√(LR/2)) | M6 |
| `basel_zone(breaches: int) -> str` | "green" for 0–4, "amber" for 5–9, "red" for ≥10 (250 observations) | FR-007 |
| `finite_sample_rate(n: int, p: float) -> float` | (k+1+w)/(n+1) with h = (n−1)p, k = ⌊h⌋, w = h − k | M7 |

## Guarantees the tests may rely on

1. **No look-ahead (FR-012, V4)**: `var_forecasts(pnl, params)[t]` depends only on `pnl[:t-1]`, that
   is x₁ … x_{t−1}. Changing any xₛ with s ≥ t, or any close Cₛ with s ≥ t, leaves it bit-for-bit
   identical.
2. **Determinism (FR-013)**: the same inputs always give identical floats.
3. **Parameters are honoured**: λ, n, W and p are taken from `params`, never from constants. V1 uses
   `Params(lam=0.94, pool=5, warmup=2, p=0.01)`.
4. **Quantile edge**: when k+2 > n, Q = z₍ₖ₊₁₎.
5. **No flooring**: VaR is returned as computed, even if ≤ 0.

## V1 worked call (spec Verification Expectations)

```python
from risk_service.core import Params, pnl_series, backtest
closes = {"XYZ": [100, 101, 99, 100, 97, 98, 99, 96, 93]}
pnl = pnl_series(closes, {"XYZ": 10})          # [10, -20, 10, -30, 10, 10, -30, -30]
bt = backtest(pnl, Params(lam=0.94, pool=5, warmup=2, p=0.01))
# bt.rows == [BacktestRow(t=8, forecast_var≈33.3085, pnl=-30, breach=False)]
```

===== END FILE: specs/001-portfolio-var-backtest/contracts/calculation-api.md =====

===== BEGIN FILE: specs/001-portfolio-var-backtest/contracts/http-api.md =====
# Contract: Risk Service HTTP API

- **Base URL**: `http://127.0.0.1:18110`. The service binds to 127.0.0.1 only; inside the compose
  network it is reachable as `risk-service:18110`.
- **Requests**: all are read-only. TraderX is only ever called with GET.
- **Responses**: JSON, UTF-8. Numbers are unrounded IEEE-754 doubles, written so they round-trip
  exactly.

## Endpoints

| Method and path | Purpose | Spec |
|---|---|---|
| `GET /` | The risk page (static HTML and JavaScript, no external assets) | FR-017 |
| `GET /health` | `{"status":"ok","data_sha256":"9ea2…ce3","synthetic":true}` | — |
| `GET /api/v1/accounts` | `{"accounts":[{"id":22214,"displayName":"Test Account 20"},…],"provenance":{…}}`, passed through from TraderX for the account picker. Returns 503 `POSITIONS_UNAVAILABLE` if TraderX is down. | FR-017 |
| `GET /api/v1/risk/accounts/{accountId}` | RiskResult for a TraderX account | FR-001 – FR-016 |
| `POST /api/v1/risk/positions` | RiskResult for a caller-supplied list. Body: `{"positions":[{"security":"MS","quantity":1000}, …]}` | FR-020 |

`accountId` must be a decimal integer. Anything else returns 400 `INVALID_REQUEST`.

## Outcome → HTTP status

| outcome | status | current / track_record / verdict |
|---|---|---|
| `OK` | 200 | present |
| `NO_OPEN_POSITIONS` | 200 | null |
| `ACCOUNT_NOT_FOUND` | 404 | null |
| `MISSING_PRICE_HISTORY` | 422 | null; also `missing_securities` (sorted list) |
| `ZERO_VOLATILITY` | 422 | null |
| `POSITIONS_UNAVAILABLE` | 503 | null |
| `INVALID_REQUEST` | 400 | null |

Every response carries `provenance`, including errors.

## Outcome precedence (normative)

When more than one outcome could apply, checks run in this order and the first match wins:

1. `INVALID_REQUEST` (400): the caller-supplied body is malformed, a quantity is not a finite
   number, a security is empty, or a security appears twice. On the account path,
   `accountId` is not a decimal integer.
2. `POSITIONS_UNAVAILABLE` (503), account path only: the TraderX account lookup or the position
   lookup failed (connection error, a 5 s timeout, or a 5xx response).
3. `ACCOUNT_NOT_FOUND` (404), account path only: the TraderX account service answered 404. The
   position service is not used for this, because it returns an empty list for unknown accounts.
4. Positions with quantity 0 are dropped and are not checked any further.
5. `NO_OPEN_POSITIONS` (200): no positions remain after step 4.
6. `MISSING_PRICE_HISTORY` (422): one or more remaining securities are not in the CSV.
   `missing_securities` lists **every** such security, sorted ascending. A zero-quantity
   position in an unpriced ticker was dropped in step 4 and is not reported.
7. `ZERO_VOLATILITY` (422): exactly when σ²_{W+1} = 0 (spec M3), that is, every warm-up P&L
   x₁ … x_W is 0. There is no other trigger: if σ²_{W+1} > 0, every later σ² is at least
   λ·σ²ₛ > 0.
8. `OK` (200).

## RiskResult example (OK, trimmed)

```json
{
  "outcome": "OK",
  "message": "One-day 99% VaR computed on SYNTHETIC price history.",
  "account": {"id": 22214, "displayName": "Test Account 20"},
  "provenance": {
    "data": "SYNTHETIC price history - not real market data",
    "synthetic": true,
    "seed": 20261117,
    "data_file": "specs/001-portfolio-var-backtest/data/synthetic_prices_seed20261117.csv",
    "data_sha256": "9ea2eab18bc0bf108fffb90245fd7f51a07e0fa16e52d49564e20c50e0718ce3",
    "method": "filtered historical simulation, EWMA λ=0.94",
    "lambda": 0.94, "pool_size": 250, "warmup": 100,
    "confidence": 0.99, "horizon_days": 1,
    "quantile_rule": "linear interpolation, position (n−1)p",
    "as_of_date": "2026-11-13",
    "position_source": "TraderX account",
    "positions_read_at": "2026-11-18T15:04:05Z"
  },
  "current": {
    "var_usd": 1234.56,
    "data_as_of": "2026-11-13",
    "forecast_for": "2026-11-16",
    "positions": [
      {"security": "C",   "quantity": -2000, "price": 58.6,  "market_value": -117200.0},
      {"security": "IBM", "quantity": -100,  "price": 187.4, "market_value": -18740.0},
      {"security": "MS",  "quantity": 1000,  "price": 91.1,  "market_value": 91100.0}
    ],
    "net_market_value": -44840.0
  },
  "track_record": [
    {"day": 351, "date": "2025-12-01", "forecast_var_usd": 1200.0, "realised_pnl_usd": -150.0, "breach": false}
  ],
  "verdict": {
    "observations": 250, "breaches": 3, "breach_rate": 0.012,
    "expected_breaches_nominal": 2.5,
    "expected_breaches_finite_sample": 3.476095617529881,
    "finite_sample_rate": 0.013904382470119523,
    "kupiec": {"lr": 0.0949, "p_value": 0.758, "null_p": 0.01,
               "critical_value": 3.841458820694124, "reject_5pct": false, "direction": null},
    "basel_zone": "green",
    "note": "<fixed note text below>"
  }
}
```

The VaR, dates and P&L values above are placeholders that only show the shape. They are not
expected values. The as-of prices do match the snapshot closes.

## Fixed verdict note (FR-016, exact text)

> A correct implementation of this method breaches about 1.39% of days (3.5 per 250), not 1%,
> because the 1% quantile of a 250-day pool sits between the 3rd and 4th worst outcomes. Such a
> model reaches the amber zone or worse roughly a quarter of the time, so amber alone does not
> prove the model wrong. Kupiec is tested against the nominal 1%.

## Caller-supplied body rules (FR-020)

- `positions` must be a list (it may be empty, which gives `NO_OPEN_POSITIONS`).
- Each item has a `security` (a non-empty string) and a `quantity` (a finite JSON number).
- A security repeated in the list returns `INVALID_REQUEST`.
- `account` is absent from the response. Provenance has `position_source = "caller-supplied"` and
  `positions_read_at = null`.

===== END FILE: specs/001-portfolio-var-backtest/contracts/http-api.md =====

===== BEGIN FILE: specs/001-portfolio-var-backtest/contracts/data-model.md =====
# Data Model: 001 Portfolio Risk and VaR Track Record

Nothing is persisted. The only stored data is the frozen CSV, which is read only. Every entity
below is computed per request, or read from TraderX per request.

## SyntheticPriceHistory (read only; spec M1 and FR-014)

| Field | Type | Rule |
|---|---|---|
| dates | list of ISO dates, length 601 | Monday–Friday; first 2024-07-26, last (as-of) 2026-11-13; index s = 0…600 |
| closes | map ticker → list of 601 floats | 20 tickers in snapshot order; values parsed from 4-decimal text |
| sha256 | hex string | must equal `9ea2eab18bc0bf108fffb90245fd7f51a07e0fa16e52d49564e20c50e0718ce3`, or the service does not start |
| label | constant | "SYNTHETIC price history - not real market data" |

## Account (read from TraderX account-service)

| Field | Type | Source |
|---|---|---|
| id | integer | `GET /account/{id}` → `id` |
| displayName | string | → `displayName` |

## Position

| Field | Type | Rule |
|---|---|---|
| security | string | ticker; must be unique within one list |
| quantity | finite number, signed | long > 0, short < 0; quantity 0 is dropped (contracts/http-api.md § Outcome precedence, step 4) |
| price | float | close on the as-of date (s = 600) from the CSV |
| market_value | float | quantity × price |

Positions come from TraderX `GET /positions/{accountId}` (fields `security` and `quantity`), or
from the caller (FR-020). They are held constant over the whole window.

## ModelSettings (constant; spec M3–M5)

λ = 0.94, pool n = 250, warm-up W = 100, p = 0.01, confidence 99%, horizon 1 day, backtest B = 250,
and the quantile rule "linear interpolation, position (n−1)p".

## Provenance (attached to every result; FR-015)

| Field | Value |
|---|---|
| data | "SYNTHETIC price history - not real market data" |
| synthetic | true |
| seed | 20261117 |
| data_file | `specs/001-portfolio-var-backtest/data/synthetic_prices_seed20261117.csv` |
| data_sha256 | as above |
| method | "filtered historical simulation, EWMA λ=0.94" |
| lambda, pool_size, warmup, confidence, horizon_days, quantile_rule | ModelSettings |
| as_of_date | "2026-11-13" |
| position_source | "TraderX account" or "caller-supplied" |
| positions_read_at | UTC ISO-8601 timestamp for the TraderX path; null for caller-supplied input or when nothing was read |

## CurrentRisk (spec M5, day N+1; FR-001 and FR-002)

| Field | Type |
|---|---|
| var_usd | float, unrounded |
| data_as_of | "2026-11-13" |
| forecast_for | "2026-11-16" (the next weekday after the as-of date) |
| positions | list of Position (security, quantity, price, market_value), sorted by security |
| net_market_value | float, the sum of market values |

## BacktestRow (FR-004 and FR-005)

| Field | Type | Rule |
|---|---|---|
| day | integer t | 351…600 |
| date | ISO date | dates[t]; the row is dated by the day it forecasts |
| forecast_var_usd | float | VaRₜ (M5) |
| realised_pnl_usd | float | xₜ (M2) |
| breach | boolean | xₜ < −VaRₜ on unrounded values |

There are exactly 250 rows, in ascending order of t.

## Verdict (FR-006, FR-007 and FR-016)

| Field | Value |
|---|---|
| observations | 250 |
| breaches | count of breach = true |
| breach_rate | breaches / 250 |
| expected_breaches_nominal | 2.5 |
| expected_breaches_finite_sample | 250 × finite_sample_rate ≈ 3.476096, shown as 3.5 |
| finite_sample_rate | (k+1+w)/(n+1) with h=(n−1)p ≈ 0.0139044 (M7); compared within 1e-9 |
| kupiec.lr, kupiec.p_value | M6 |
| kupiec.null_p | 0.01 |
| kupiec.critical_value | 3.841458820694124 |
| kupiec.reject_5pct | lr > critical_value |
| kupiec.direction | "too_many" / "too_few" if rejected, otherwise null |
| basel_zone | "green" (0–4), "amber" (5–9), "red" (≥10) |
| note | the fixed text in contracts/http-api.md |

## RiskResult (the envelope for every response)

| Field | Present when |
|---|---|
| outcome | always: one of `OK`, `ACCOUNT_NOT_FOUND`, `NO_OPEN_POSITIONS`, `MISSING_PRICE_HISTORY`, `ZERO_VOLATILITY`, `POSITIONS_UNAVAILABLE`, `INVALID_REQUEST` |
| message | always, human-readable |
| provenance | always |
| account | account path, when the account was found |
| current, track_record, verdict | only when outcome = OK; otherwise absent or null, never 0 |
| missing_securities | only when outcome = MISSING_PRICE_HISTORY |

There is no stored state, so there are no state changes. Precedence between outcomes is in
contracts/http-api.md § Outcome precedence.

===== END FILE: specs/001-portfolio-var-backtest/contracts/data-model.md =====

===== BEGIN FILE: specs/001-portfolio-var-backtest/contracts/test-harness.md =====
# Contract: Test Harness

This file holds only what the tests need in order to run: paths, environment variables, commands,
tiers and file formats. It contains no expected values. Every number a test checks comes from
`spec.md` (Verification Expectations V1–V6, Success Criteria) or from the other contracts
(`calculation-api.md`, `http-api.md`, `data-model.md`).

## Layout and runtime

- All commands run from the repository root.
- **Python**: 3.9 or later. **Test runner**: pytest. No other third-party packages: the tests
  must run offline (constitution III).
- **Implementation package**: `risk_service`, found under `risk-service/`. Tests import it as
  `from risk_service.core import …` with `PYTHONPATH=risk-service`.
- **Test folders**:

| Folder | Tier | Needs the running stack | Scope |
|---|---|---|---|
| `tests/unit/` | 1 | no | calculation contract (`risk_service.core`) |
| `tests/oracle/` | 1 (and 2) | no for the offline comparison; yes for any HTTP comparison | independent implementation of spec M2–M7, compared with `risk_service.core` and, where the stack is up, with the HTTP API |
| `tests/integration/` | 2 | yes | HTTP API, outcomes, provenance, baseline comparison |

## Commands

| Tier | Command |
|---|---|
| 1 | `PYTHONPATH=risk-service python3 -m pytest tests/unit tests/oracle -q` |
| 2 | `RISK_BASE_URL=http://127.0.0.1:18110 TRADERX_BASE_URL=http://127.0.0.1:8080 PYTHONPATH=risk-service python3 -m pytest tests/integration -q` |

## Environment variables

| Variable | Used by | Meaning | Default when unset |
|---|---|---|---|
| `PYTHONPATH` | all tiers | must include `risk-service` | — (required) |
| `RISK_BASE_URL` | tier 2 | base URL of the risk service (`http-api.md`) | `http://127.0.0.1:18110` |
| `TRADERX_BASE_URL` | tier 2 | the TraderX ingress, used for the baseline comparison | `http://127.0.0.1:8080` |
| `RISK_DATA_DIR` | tiers 1 and 2 | folder holding the frozen data file | `specs/001-portfolio-var-backtest/data` |

## Frozen data file

- **Path**: `$RISK_DATA_DIR/synthetic_prices_seed20261117.csv`.
- **Checksums**: `$RISK_DATA_DIR/SHA256SUMS`. Tests may verify the file against it before use.
- **Format**: UTF-8 text with `\n` line endings. The header row is `date`, then 20 ticker columns
  in this order: AAPL, MSFT, AMZN, GOOGL, META, NVDA, TSLA, IBM, BAC, C, JPM, GS, MS, UBS, DB,
  COF, DFS, FNMA, FIS, FNF. After it come 601 data rows in ascending date order. Dates are
  ISO `YYYY-MM-DD`. Prices are decimal text with 4 decimal places, parsed with `float()`.
- **Day index**: row k (0-based, excluding the header) is synthetic business day s = k. That gives
  s = 0 … 600, and s = 600 is the as-of date.
- Generation parameters are in `$RISK_DATA_DIR/synthetic_prices_seed20261117.meta.json`.

## Baseline responses (SC-007)

- **Path**: `specs/001-portfolio-var-backtest/validation/runs/baseline-before.json`.
- **What it is**: the TraderX responses captured from the running baseline stack before the
  feature's stack replaces it. That stack is a separate checkout of the same upstream commit
  (finos/traderX@d6e7fe4). Tests read this file. They never write it.
- **Format**: one JSON object.

```json
{
  "captured_at": "<UTC ISO-8601 timestamp>",
  "source": {
    "stack": "traderx-state-008",
    "note": "separate checkout of finos/traderX@d6e7fe4",
    "base_url": "http://127.0.0.1:8080"
  },
  "responses": [
    {"path": "<request path>", "status": <HTTP status code>, "body": <parsed JSON, or a string when the body is not JSON>}
  ]
}
```

- **Paths captured, in this order**:
  - `/account-service/account/`
  - `/account-service/account/22214`
  - `/account-service/account/52355`
  - `/account-service/account/44044`
  - `/account-service/account/99999`
  - `/position-service/positions/22214`
  - `/position-service/positions/52355`
  - `/price-publisher/prices`
- **Comparison rules**: these are defined in spec SC-007, not here. The "after" request for each
  entry is `TRADERX_BASE_URL` + `path`.

## Determinism inside tests

Any random numbers a test draws come from a seed fixed in the test file (spec V2 and V4).

===== END FILE: specs/001-portfolio-var-backtest/contracts/test-harness.md =====

===== BEGIN FILE: specs/001-portfolio-var-backtest/data/synthetic_prices_seed20261117.meta.json =====
{
  "label": "SYNTHETIC price history - not real market data",
  "synthetic": true,
  "feature": "001-portfolio-var-backtest",
  "spec_section": "M1",
  "seed": 20261117,
  "rng": "numpy.random.default_rng (PCG64); draw order: u[600], then e[600,20] row-major",
  "numpy_version_used": "1.25.2",
  "calendar": "Monday-Friday, no holidays (synthetic calendar)",
  "first_date": "2024-07-26",
  "as_of_date": "2026-11-13",
  "n_closes": 601,
  "tickers": [
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL",
    "META",
    "NVDA",
    "TSLA",
    "IBM",
    "BAC",
    "C",
    "JPM",
    "GS",
    "MS",
    "UBS",
    "DB",
    "COF",
    "DFS",
    "FNMA",
    "FIS",
    "FNF"
  ],
  "model": {
    "factor": "GARCH(1,1)",
    "alpha": 0.08,
    "beta": 0.9,
    "omega": 2.000000000000002e-06,
    "long_run_daily_vol": 0.01,
    "h_initial": 0.0001,
    "loading": 1.0,
    "idiosyncratic_daily_vol": 0.015,
    "drift": 0.0,
    "innovations": "i.i.d. standard normal"
  },
  "anchor": "close on as_of_date equals traderx/price-publisher/data/snapshot-prices.json closePrice",
  "decimals": 4,
  "csv_file": "synthetic_prices_seed20261117.csv",
  "csv_sha256": "9ea2eab18bc0bf108fffb90245fd7f51a07e0fa16e52d49564e20c50e0718ce3",
  "authoritative": "the CSV file; regenerating with another library version may differ"
}

===== END FILE: specs/001-portfolio-var-backtest/data/synthetic_prices_seed20261117.meta.json =====

===== BEGIN FILE: specs/001-portfolio-var-backtest/data/SHA256SUMS =====
9ea2eab18bc0bf108fffb90245fd7f51a07e0fa16e52d49564e20c50e0718ce3  synthetic_prices_seed20261117.csv
0d57c8ab0c54e89cad486c6c69fd545257ceb8f79695edcff3343a92ea4afda2  synthetic_prices_seed20261117.meta.json

===== END FILE: specs/001-portfolio-var-backtest/data/SHA256SUMS =====

===== BEGIN FILE SAMPLE: specs/001-portfolio-var-backtest/data/synthetic_prices_seed20261117.csv =====
date,AAPL,MSFT,AMZN,GOOGL,META,NVDA,TSLA,IBM,BAC,C,JPM,GS,MS,UBS,DB,COF,DFS,FNMA,FIS,FNF
2024-07-26,187.6006,580.5846,222.5185,204.5458,204.6937,1227.6438,223.5771,296.1071,17.3149,49.0595,150.9219,511.2266,42.5727,26.9890,35.1786,332.9842,184.7165,2.0219,82.7519,42.9949
2024-07-29,193.1573,578.1579,225.0685,203.8483,206.1067,1195.9863,224.3010,297.9942,17.8432,50.9729,152.8999,515.9642,42.4403,27.3261,36.0560,326.1647,180.7970,2.0762,83.6664,44.2271
2024-07-30,190.7756,558.6695,224.5350,207.3821,204.0046,1196.6629,223.6984,298.5221,17.9730,51.1201,153.8468,509.0569,43.0647,26.1872,35.8255,318.8593,178.5177,2.0085,83.4229,43.5075
... (595 rows omitted; the tests read the full file from its path) ...
2026-11-11,201.9778,440.6863,195.6313,165.4668,531.4287,951.0400,179.5447,193.1995,42.1318,59.2671,198.1265,438.1064,98.0101,30.9638,17.4810,158.4420,131.0623,1.1417,77.2215,51.3395
2026-11-12,200.1018,438.5072,191.7439,168.5665,519.7048,924.2601,172.7245,190.2611,41.6778,57.8281,194.2441,424.5403,93.2171,31.0717,17.0823,153.0609,129.1316,1.1475,75.0499,50.3130
2026-11-13,192.8000,431.6000,185.5000,167.1000,503.2000,910.8000,172.0000,187.4000,41.7000,58.6000,195.8000,404.2000,91.1000,29.9000,17.0500,150.3000,127.6500,1.1450,75.2000,49.9500
===== END FILE SAMPLE: specs/001-portfolio-var-backtest/data/synthetic_prices_seed20261117.csv =====

===== BEGIN FILE: tests/oracle/oracle_independent_var.py =====
"""Independent implementation of spec M2-M7 for oracle comparisons."""

from dataclasses import dataclass
from math import erfc, floor, log, sqrt
from typing import Dict, Mapping, Optional, Sequence


@dataclass(frozen=True)
class Params:
    lam: float = 0.94
    pool: int = 250
    warmup: int = 100
    p: float = 0.01


class ZeroVolatilityError(ValueError):
    pass


class InsufficientHistoryError(ValueError):
    pass


@dataclass(frozen=True)
class BacktestRow:
    t: int
    forecast_var: float
    pnl: float
    breach: bool


@dataclass(frozen=True)
class Backtest:
    rows: list
    current_var: float


@dataclass(frozen=True)
class Kupiec:
    lr: float
    p_value: float
    reject: bool
    direction: Optional[str]


def pnl_series(
    closes: Mapping[str, Sequence[float]],
    positions: Mapping[str, float],
) -> list:
    """Compute constant-position daily dollar P&L (spec M2)."""
    if not closes:
        raise ValueError("closes must not be empty")

    lengths = {len(series) for series in closes.values()}
    if len(lengths) != 1 or next(iter(lengths)) < 2:
        raise ValueError("all close series must have the same length of at least two")

    for ticker in positions:
        if ticker not in closes:
            raise KeyError(ticker)

    close_count = next(iter(lengths))
    result = []
    for s in range(1, close_count):
        day_pnl = 0.0
        for ticker in sorted(positions):
            day_pnl += positions[ticker] * (
                closes[ticker][s] - closes[ticker][s - 1]
            )
        result.append(day_pnl)
    return result


def ewma_sigmas(pnl: Sequence[float], params: Params) -> Dict[int, float]:
    """Compute lagged EWMA standard deviations (spec M3)."""
    n_days = len(pnl)
    if n_days < params.warmup:
        raise InsufficientHistoryError("not enough observations for warm-up")

    variance = sum(value * value for value in pnl[: params.warmup]) / params.warmup
    if variance == 0.0:
        raise ZeroVolatilityError("warm-up volatility is zero")

    sigmas = {params.warmup + 1: sqrt(variance)}
    for s in range(params.warmup + 1, n_days + 1):
        variance = params.lam * variance + (1.0 - params.lam) * pnl[s - 1] ** 2
        sigmas[s + 1] = sqrt(variance)
    return sigmas


def residuals(pnl: Sequence[float], params: Params) -> Dict[int, float]:
    """Compute filtered residuals z_s (spec M3)."""
    sigmas = ewma_sigmas(pnl, params)
    return {
        s: pnl[s - 1] / sigmas[s]
        for s in range(params.warmup + 1, len(pnl) + 1)
    }


def interp_quantile(values: Sequence[float], p: float) -> float:
    """Compute the position-(n-1)p linearly interpolated quantile (spec M4)."""
    if not values:
        raise ValueError("quantile requires at least one value")

    ordered = sorted(values)
    h = (len(ordered) - 1) * p
    k = floor(h)
    weight = h - k
    quantile = ordered[k]
    if k + 1 < len(ordered):
        quantile += weight * (ordered[k + 1] - quantile)
    return quantile


def var_forecasts(pnl: Sequence[float], params: Params) -> Dict[int, float]:
    """Compute historical-simulation VaR forecasts through day N+1 (spec M5)."""
    n_days = len(pnl)
    if n_days < params.warmup + params.pool:
        raise InsufficientHistoryError("not enough observations for the residual pool")

    sigmas = ewma_sigmas(pnl, params)
    standardized = residuals(pnl, params)
    forecasts = {}
    for t in range(params.warmup + params.pool + 1, n_days + 2):
        pool = [standardized[s] for s in range(t - params.pool, t)]
        forecasts[t] = -sigmas[t] * interp_quantile(pool, params.p)
    return forecasts


def backtest(pnl: Sequence[float], params: Params) -> Backtest:
    """Create backtest rows and the following-day current VaR (spec M5)."""
    forecasts = var_forecasts(pnl, params)
    n_days = len(pnl)
    rows = []
    for t in range(params.warmup + params.pool + 1, n_days + 1):
        forecast = forecasts[t]
        realised = pnl[t - 1]
        rows.append(
            BacktestRow(
                t=t,
                forecast_var=forecast,
                pnl=realised,
                breach=realised < -forecast,
            )
        )
    return Backtest(rows=rows, current_var=forecasts[n_days + 1])


def kupiec(breaches: int, T: int, p: float) -> Kupiec:
    """Compute the unconditional-coverage statistic and its chi-square p-value (spec M6)."""
    observed_rate = breaches / T
    null_log_likelihood = (T - breaches) * log(1.0 - p)
    if breaches:
        null_log_likelihood += breaches * log(p)

    observed_log_likelihood = 0.0
    if T - breaches:
        observed_log_likelihood += (T - breaches) * log(1.0 - observed_rate)
    if breaches:
        observed_log_likelihood += breaches * log(observed_rate)

    lr = -2.0 * (null_log_likelihood - observed_log_likelihood)
    reject = lr > 3.841458820694124
    direction = None
    if reject:
        direction = "too_many" if breaches > T * p else "too_few"

    return Kupiec(
        lr=lr,
        p_value=erfc(sqrt(lr / 2.0)),
        reject=reject,
        direction=direction,
    )


def basel_zone(breaches: int) -> str:
    """Return the 250-observation Basel traffic-light zone (spec FR-007)."""
    if breaches <= 4:
        return "green"
    if breaches <= 9:
        return "amber"
    return "red"


def finite_sample_rate(n: int, p: float) -> float:
    """Compute the finite-sample quantile coverage approximation (spec M7)."""
    h = (n - 1) * p
    k = floor(h)
    weight = h - k
    return (k + 1 + weight) / (n + 1)

===== END FILE: tests/oracle/oracle_independent_var.py =====

===== BEGIN FILE: tests/oracle/test_oracle_independent_comparison.py =====
import csv
import os
from pathlib import Path

import pytest

from risk_service import core as service
import oracle_independent_var as oracle


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = (
    REPOSITORY_ROOT / "specs/001-portfolio-var-backtest/data"
)

SEEDED_ACCOUNTS = (
    (22214, {"C": -2000.0, "IBM": -100.0, "MS": 1000.0}),
    (52355, {"BAC": -2400.0}),
)


def _data_path():
    configured = Path(os.environ.get("RISK_DATA_DIR", str(DEFAULT_DATA_DIR)))
    if not configured.is_absolute():
        configured = REPOSITORY_ROOT / configured
    return configured / "synthetic_prices_seed20261117.csv"


def _published_closes():
    with _data_path().open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        tickers = [name for name in reader.fieldnames if name != "date"]
        closes = {ticker: [] for ticker in tickers}
        for row in reader:
            for ticker in tickers:
                closes[ticker].append(float(row[ticker]))
    return closes


@pytest.mark.parametrize("account_id,positions", SEEDED_ACCOUNTS)
def test_published_history_agrees_with_independent_implementation(
    account_id, positions
):
    closes = _published_closes()

    service_pnl = service.pnl_series(closes, positions)
    oracle_pnl = oracle.pnl_series(closes, positions)

    service_backtest = service.backtest(service_pnl, service.Params())
    oracle_backtest = oracle.backtest(oracle_pnl, oracle.Params())

    # spec V3: every current VaR agrees within $0.01.
    assert abs(service_backtest.current_var - oracle_backtest.current_var) <= 0.01

    # spec FR-004 and V3: each seeded account has 250 compared backtest days.
    assert len(service_backtest.rows) == 250
    # spec FR-004 and V3: each seeded account has 250 compared backtest days.
    assert len(oracle_backtest.rows) == 250

    for expected_day, service_row, oracle_row in zip(
        range(351, 601), service_backtest.rows, oracle_backtest.rows
    ):
        # contracts/calculation-api.md indexing convention: rows are ascending by day t.
        assert service_row.t == expected_day
        # contracts/calculation-api.md indexing convention: rows are ascending by day t.
        assert oracle_row.t == expected_day
        # spec V3 and SC-004: every backtest forecast agrees within $0.01.
        assert abs(service_row.forecast_var - oracle_row.forecast_var) <= 0.01
        # spec V3 and SC-004: breach flags are identical on all account-days.
        assert service_row.breach is oracle_row.breach

    service_breaches = sum(row.breach for row in service_backtest.rows)
    oracle_breaches = sum(row.breach for row in oracle_backtest.rows)

    # spec V3: verdict breach counts are identical.
    assert service_breaches == oracle_breaches

    service_kupiec = service.kupiec(service_breaches, T=250, p=0.01)
    oracle_kupiec = oracle.kupiec(oracle_breaches, T=250, p=0.01)

    # spec V3: Kupiec LR agrees within 1e-6.
    assert abs(service_kupiec.lr - oracle_kupiec.lr) <= 1e-6
    # spec V3: Kupiec p-value agrees within 1e-6.
    assert abs(service_kupiec.p_value - oracle_kupiec.p_value) <= 1e-6
    # spec V3: verdict rejection decisions are identical.
    assert service_kupiec.reject is oracle_kupiec.reject
    # spec V3: verdict rejection directions are identical.
    assert service_kupiec.direction == oracle_kupiec.direction
    # spec V3: Basel verdict fields are identical.
    assert service.basel_zone(service_breaches) == oracle.basel_zone(oracle_breaches)
    # spec V3 and M7: finite-sample verdict rates are identical.
    assert service.finite_sample_rate(250, 0.01) == oracle.finite_sample_rate(
        250, 0.01
    )

===== END FILE: tests/oracle/test_oracle_independent_comparison.py =====

Answer from the text above only. Do not run commands, read files or use tools.
