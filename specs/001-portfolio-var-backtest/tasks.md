---
description: "Task list for 001 Portfolio Risk and VaR Track Record"
---

# Tasks: Portfolio Risk and VaR Track Record for TraderX Accounts

**Input**: Design documents from `specs/001-portfolio-var-backtest/` (plan.md, spec.md,
research.md, contracts/ including contracts/data-model.md and contracts/test-harness.md,
quickstart.md)

**Prerequisites**: plan.md, spec.md, research.md, contracts/, quickstart.md

**Tests**: The tests are required by the constitution (Principle V) and by the spec (V1–V6). They
are **written by qwen3-coder:30b**, through the runner, and never by Claude. The implementing side
(Claude) has no task that creates or edits anything under `tests/`.

**Owners**: every task names one owner.

- **Author**: the human; makes commits and decisions.
- **Claude**: the implementing model.
- **qwen**: qwen3-coder:30b, run by the author through `run_validator.py`.

**Order rule (constitution workflow, step 4)**:

1. The author approves and commits this file (T000a). No other open task starts before that.
2. Claude builds the setup and the validator tooling (T001–T005). The author reviews the runner
   and prompts and approves the qwen run (T006).
3. qwen's tests are generated and committed, and must fail against an empty implementation
   (T007–T013).
4. Only then may Claude implement: the calculation core first (Phase 3, offline), then the
   service shell and the page (Phase 4 onward).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US4 from spec.md
- Paths are relative to the repository root. `FEAT` = `specs/001-portfolio-var-backtest`

---

## Phase 0: Prerequisites (T000 done before this file; T000a is the approval gate)

- [x] T000 Synthetic price generator, CSV, meta.json and SHA256SUMS in `FEAT/data/` (owner: Claude; reviewed, run and committed by the author in 86acd2d). This is the recorded Principle I deviation in plan.md Complexity Tracking.
- [ ] T000a Author reviews, approves and commits `FEAT/tasks.md` with DCO sign-off (owner: Author). Constitution workflow gate 4. It comes before T001: no other open task starts until this commit exists (constitution I).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: settings enforcement, project skeleton, deployment wiring and validator tooling. None
of these tasks touch `tests/`.

- [ ] T001 Create `.claude/settings.json` with exactly `{"permissions": {"deny": ["Edit(/tests/**)"]}}` (owner: Claude; the author reviews and commits). The leading `/` anchors the pattern to the repository root. One `Edit(...)` rule covers Edit, Write and NotebookEdit. It is expected to also cover Bash `cat`/`sed`/`tee` and `>` targets; this is verified in T011, not assumed (research R11).
- [ ] T002 [P] Create the empty package skeleton `risk-service/risk_service/__init__.py`, containing only a module docstring that says the price history is synthetic, and the empty folder `risk-service/risk_service/static/` (owner: Claude). Do not create `core.py` yet: the tests must fail on import at T012.
- [ ] T003 [P] Create `deploy/tau.override.yml` (owner: Claude). It must:
  - give all 19 baseline services `ports: !override` bindings on `127.0.0.1`, copied entry for entry from `/home/research/work/traderx-local-only.override.yml`, the override the current local stack uses (research R3);
  - add `risk-service` with `build.context: ../../risk-service`, port `"127.0.0.1:18110:18110"`, volume `../../specs/001-portfolio-var-backtest/data:/data:ro`, environment `RISK_DATA_DIR=/data`, `TRADERX_ACCOUNT_URL=http://account-service:18088`, `TRADERX_POSITION_URL=http://position-service:18090`, and `depends_on` account-service and position-service.

  Check with `docker compose -f traderx/pricing-awareness-market-data/docker-compose.yml -f deploy/tau.override.yml --project-name traderx-tau config`. Do **not** run `up`.
- [ ] T004 [P] Create `risk-service/Dockerfile` (owner: Claude):
  - `FROM python:3.10-slim@sha256:2ee0fb8794bf82af1b2db168ada5869b4c27d17720dd3b155b56c111fb4a38ae`;
  - no `pip install`;
  - `COPY risk_service /app/risk_service`, `WORKDIR /app`, `EXPOSE 18110`;
  - `CMD ["python", "-m", "risk_service.server"]`.
- [ ] T005 Create the validator runner `FEAT/validation/validator/run_validator.py` and the prompt files `FEAT/validation/validator/prompts/common.md`, `round-1-unit.md`, `round-2-oracle.md` and `round-3-integration.md` (owner: Claude; the author reviews all prompts before T007). The runner:
  - uses the standard library only, calling `http://127.0.0.1:11434/api/chat` with model `qwen3-coder:30b` and options `temperature 0`, `seed 20261117`, `num_ctx 65536`;
  - builds each prompt from **exactly** the canonical input list in research R9: the constitution, spec.md, the four contracts (`contracts/calculation-api.md`, `contracts/http-api.md`, `contracts/data-model.md`, `contracts/test-harness.md`), the full `meta.json` and `SHA256SUMS`, and the CSV header plus its first and last 3 rows;
  - writes `request.json` (model name and digest, options, each input path with its SHA-256) and `response.json` (raw) to `FEAT/validation/validator/round-N/`, or to `round-N/retry-M/` when called with `--retry M --note FILE`, saving the note too;
  - stops with an error if `prompt_eval_count` ≥ 0.9 × `num_ctx`, or if `done_reason` is not `stop`;
  - extracts only fenced blocks whose info string is `python file=tests/<path>`. It writes them verbatim, refuses any path outside `tests/` or containing `..`, and writes `round-N/files.sha256`;
  - takes `--round {1,2,3}` and `--dry-run` (prints the prompt size and the input list, and calls nothing).

  The round prompts assign: round 1 → `tests/unit/` (V1, V2, V4, V5, calculation-contract behaviour); round 2 → `tests/oracle/` (an independent M2–M7 implementation, plus a comparison with `risk_service.core` on the frozen CSV for 22214 and 52355 as caller-supplied positions, V3); round 3 → `tests/integration/` (V6, provenance and SC-006, SC-007, SC-008, and V3 over HTTP, using the `RISK_BASE_URL` environment variable).

  **Prompt independence rule**: Round prompts contain only the scope (which V items and SC items, which tests/ folder), the input list, and the output format. They contain no expected values, no code snippets, no function bodies, and no implementation hints. Every number the tests check comes from spec.md or the contracts, not from the prompt. Claude writes the prompts, so the author checks this before T007.

---

## Phase 2: Foundational — validator tests first (blocks all implementation)

**⚠️ CRITICAL**: no Phase 3+ task (starting with the Core-first block) may start until T013a is committed.

- [ ] T006 Author reviews `FEAT/validation/validator/run_validator.py` and the four prompt files in `FEAT/validation/validator/prompts/` against the prompt rule in T005, then approves the Qwen run (owner: Author). T006 comes before T007. Review checklist (the T005 rule, item by item):
  1. The round prompts contain only the scope (which V items and SC items, which `tests/` folder), the input list, and the output format.
  2. They contain no expected values, no code snippets, no function bodies, and no implementation hints.
  3. Every number the tests check comes from spec.md or the contracts, not from the prompt.
  4. Claude wrote the prompts, so this check is done by the author before T007 (`run_validator.py --dry-run` for each round shows the input list and the prompt size).
- [ ] T007 Run `python3 FEAT/validation/validator/run_validator.py --round 1`, which writes `tests/unit/` (owner: qwen, run by the Author). Inspect `FEAT/validation/validator/round-1/`. If the output is broken or incomplete, re-run with `--retry M --note …`. Nobody edits the generated files by hand. **Timebox**: at most 2 retries per round. Phase 2 as a whole (T006–T013) is timeboxed to about 90 minutes. If a round still fails after 2 retries, record it in `FEAT/disputes.md` with the reason, keep the last raw output, and continue. A missing round is reported as 'not yet verified' in traceability.md, never hidden.
- [ ] T008 Run `run_validator.py --round 2`, which writes `tests/oracle/` (owner: qwen, run by the Author). Same retry rule as T007. **Timebox**: at most 2 retries per round. Phase 2 as a whole (T006–T013) is timeboxed to about 90 minutes. If a round still fails after 2 retries, record it in `FEAT/disputes.md` with the reason, keep the last raw output, and continue. A missing round is reported as 'not yet verified' in traceability.md, never hidden.
- [ ] T008a Capture the baseline TraderX responses into `FEAT/validation/runs/baseline-before.json` (owner: Author; Claude may run the curl commands). Source: the running `traderx-state-008` stack at `http://127.0.0.1:8080`. Note in the file that this stack is a separate checkout (`/home/research/work/traderX-state-008`) of the same upstream commit finos/traderX@d6e7fe4. Paths, in this order: `/account-service/account/`, `/account-service/account/22214`, `/account-service/account/52355`, `/account-service/account/44044`, `/account-service/account/99999`, `/position-service/positions/22214`, `/position-service/positions/52355`, `/price-publisher/prices`. The file format is defined in `contracts/test-harness.md` § Baseline responses: `captured_at`, `source`, and `responses[]` of `{path, status, body}`. This must be done before qwen round 3 (T009) is final and before T032 stops the baseline stack. Check that the captured positions for 22214 and 52355 match the seeded positions (22214: C −2000, IBM −100, MS +1000, as stated in spec.md; 52355: BAC −2400, from `traderx/database/initialSchema.sql`, since spec.md does not list 52355's positions). Also check that 44044 returns `[]`: `/position-service/positions/44044` is not one of the captured paths, so it is checked with one extra GET. Record the check result in baseline-before.json's note field (`source.note`). A mismatch stops the task and is reported to the author. The Author commits the file.
- [ ] T009 Run `run_validator.py --round 3`, which writes `tests/integration/` (owner: qwen, run by the Author). Same retry rule as T007. **Timebox**: at most 2 retries per round. Phase 2 as a whole (T006–T013) is timeboxed to about 90 minutes. If a round still fails after 2 retries, record it in `FEAT/disputes.md` with the reason, keep the last raw output, and continue. A missing round is reported as 'not yet verified' in traceability.md, never hidden.
- [ ] T010 Create `FEAT/validation/validator/tests.sha256` with `find tests -type f | sort | xargs sha256sum`, and commit `tests/` and `FEAT/validation/validator/` together (owner: Author). The commit message carries the trailer `Assisted-by: qwen3-coder:30b via Ollama 0.40.3 (06c1097efce0)` and the author's `Signed-off-by`.
- [ ] T011 Settings probe. Run the probe in a new Claude Code session started at the repository root after .claude/settings.json is committed. A session that was already running may not reload settings. Record the session start time and the settings.json commit hash at the top of settings-probe.md. In that session, attempt P1–P6 from research R11 — Write `tests/_probe.py`, Edit an existing `tests/unit/*.py`, `echo x > tests/_probe.py`, `echo x >> tests/unit/<file>.py`, `echo x | tee tests/_probe.py`, `sed -i 's/a/a/' tests/unit/<file>.py`. Do each from the root, then again after `cd risk-service` using `../tests/…` paths (owner: Claude, observed by the Author). Record all 12 tool calls and refusal texts in `FEAT/validation/validator/settings-probe.md`.
  - **Pass**: all 12 are refused, `git status --porcelain -- tests/` is empty, and `sha256sum -c FEAT/validation/validator/tests.sha256` is all OK.
  - **On failure**: record it in `FEAT/disputes.md`. The author runs `git checkout -- tests/` and the rule is fixed before T014.
- [ ] T012 Red run, with all output saved verbatim to `FEAT/validation/validator/red-run.txt` (owner: Claude, or the Author). (a) `PYTHONPATH=risk-service python3 -m pytest tests/unit tests/oracle -q`; (b) `RISK_BASE_URL=http://127.0.0.1:18110 PYTHONPATH=risk-service python3 -m pytest tests/integration -q`, with risk-service **not running** (nothing listening on 18110). Both runs **must fail**, and for the right reason. In (a), the test cases that use `risk_service.core` fail with `ModuleNotFoundError` or `ImportError`. In (b), the risk-service requests fail with connection refused, and that expected failure is recorded in `red-run.txt`. Every test that passes in (b) with risk-service not running is listed in `red-run.txt` with the reason. A test may legitimately pass only if it calls TraderX alone and never `RISK_BASE_URL` (for example the SC-007 baseline comparison against `baseline-before.json`). A test that passes while calling `RISK_BASE_URL` is a finding for `FEAT/disputes.md`. Tests that pass without any implementation (for example oracle-only self-checks) are listed in the file. A test that passes **while** depending on `risk_service` is a finding for `FEAT/disputes.md`.
- [ ] T013 Spec-conformance read of `tests/` against spec.md and contracts/ (owner: Claude, read only). Record every test that contradicts the spec in `FEAT/disputes.md`, quoting the test line and the spec clause. Examples: a wrong quantile convention, a tolerance other than the pre-registered one, an assertion of a demo-account Basel zone. Claude does not edit anything. The Author decides each dispute (keep, or re-run the round with a note).
- [ ] T013a Commit `FEAT/validation/validator/settings-probe.md` (T011), `FEAT/validation/validator/red-run.txt` (T012) and `FEAT/disputes.md` (T013, if it exists) with DCO sign-off, then push (owner: Author). This commit is the git-history proof of constitution workflow gate 4: the validator's tests were committed first (T010) and failed against an empty implementation, before any implementation commit.

**Checkpoint**: tests are committed, fail red, and are protected. Implementation may begin.

---

## Phase 3: Core first — the calculation core, offline (Claude's first implementation block)

**Purpose**: finish the whole calculation in `risk-service/risk_service/core.py` and prove it
offline before any service shell exists. The tasks keep their user-story labels: T014 serves US1,
T021 serves US2 and T025 serves US3. All three are in the same file, so they run in sequence, not
in parallel.

**Cut line**: if time runs out, the offline core is what must be finished (see Implementation
strategy).

- [ ] T014 [US1] Implement the calculation core in `risk-service/risk_service/core.py` exactly as specified in `contracts/calculation-api.md` (owner: Claude; Python 3.9-compatible, standard library only).
  - **Types**: `Params(lam=0.94, pool=250, warmup=100, p=0.01)`, `ZeroVolatilityError`, `InsufficientHistoryError`, `BacktestRow`, `Backtest`, `Kupiec`.
  - **`pnl_series`**: sums in ascending ticker order, xₛ = Σ qᵢ·(Pᵢ,ₛ − Pᵢ,ₛ₋₁), and returns x₁ … x_N.
  - **`ewma_sigmas`**: keys W+1 … N+1. The seed is σ²_{W+1} = mean of x₁² … x_W². The recursion is σ²_{s+1} = λσ²ₛ + (1−λ)xₛ². Raises `ZeroVolatilityError` iff σ²_{W+1} = 0.
  - **`residuals`**: keys W+1 … N.
  - **`interp_quantile`**: h = (n−1)p, k = ⌊h⌋, w = h − k, Q = z₍ₖ₊₁₎ + w(z₍ₖ₊₂₎ − z₍ₖ₊₁₎), and Q = z₍ₖ₊₁₎ when k+2 > n.
  - **`var_forecasts`**: keys W+n+1 … N+1, with VaRₜ = −σₜ·Q(z_{t−n} … z_{t−1}). Raises `InsufficientHistoryError` if N < W+n. No flooring.
- [ ] T021 [US2] Add `backtest(pnl, params) -> Backtest` to `risk-service/risk_service/core.py` (owner: Claude). Rows cover t = W+n+1 … N in ascending order, and `breach = pnl_t < -forecast_var_t` on unrounded values. `current_var` = the forecast for N+1.
- [ ] T025 [US3] Add the verdict functions to `risk-service/risk_service/core.py` (owner: Claude).
  - **`kupiec(breaches, T, p)`**: LR = −2[(T−x)ln(1−p) + x ln p − (T−x)ln(1−x/T) − x ln(x/T)], with 0·ln 0 = 0. p-value = `math.erfc(math.sqrt(lr/2))`. `reject` = lr > 3.841458820694124. `direction` is "too_many" if x > 2.5 or "too_few" if x < 2.5, and only when rejected; otherwise `None`.
  - **`basel_zone(x)`**: "green" for 0–4, "amber" for 5–9, "red" for ≥10.
  - **`finite_sample_rate(n, p)`**: (k+1+w)/(n+1).
- [ ] T025a Run `PYTHONPATH=risk-service python3 -m pytest tests/unit tests/oracle -q` and save the output verbatim to `FEAT/validation/runs/core-offline.txt` (owner: Claude). V1, V2, V3 (the offline part), V4 and V5 must pass here. Failures are fixed only in `risk-service/risk_service/core.py`; a suspected test error goes to `FEAT/disputes.md`. Only after this run passes do the prices, client, results, server and page tasks (Phase 4 onward) start.

**Checkpoint**: the calculation core is complete and verified offline. This is the minimum
deliverable if time runs out.

---

## Phase 4: User Story 1 — See an account's current one-day 99% VaR (Priority: P1) 🎯 MVP

**Prerequisite**: Phase 3 (T014, and the T025a run passing). The tasks below build the service
shell and the page on top of the finished core.

**Goal**: pick an account, see its VaR in dollars with the positions, prices, market values and net
value it was computed from, and the two dates. Covers FR-001–FR-003, FR-008–FR-011, FR-020 and
M2–M5.

**Independent Test**: `tests/unit` V1 (VaR₈ = 33.3085 ± 0.0001) and V4 pass. `GET
/api/v1/risk/accounts/22214` returns `OK` with 3 positions at C 58.6, IBM 187.4 and MS 91.1, and
`forecast_for` 2026-11-16. 99999 gives 404 and 44044 gives `NO_OPEN_POSITIONS`.

- [ ] T015 [P] [US1] Implement `risk-service/risk_service/prices.py` (owner: Claude).
  - Load `synthetic_prices_seed20261117.csv` from `$RISK_DATA_DIR`, defaulting to `specs/001-portfolio-var-backtest/data` resolved from the repository root.
  - Compute its SHA-256 and raise at startup unless it equals `9ea2eab18bc0bf108fffb90245fd7f51a07e0fa16e52d49564e20c50e0718ce3`.
  - Parse the dates and the 20 ticker columns with `float()`, and expose `closes: dict[str, list[float]]`, `dates`, `as_of = 2026-11-13`, and `forecast_for` = the next weekday after the as-of date (2026-11-16).
- [ ] T016 [P] [US1] Implement `risk-service/risk_service/traderx_client.py` (owner: Claude). GET calls only, with `urllib` and a 5 s timeout:
  - `get_account(id)`: dict, or `None` on 404;
  - `get_positions(id)`: a list of `{security, quantity}`;
  - `list_accounts()`.

  A connection error, timeout or 5xx raises `TraderXUnavailable`. Base URLs come from `TRADERX_ACCOUNT_URL` and `TRADERX_POSITION_URL`, defaulting to `http://127.0.0.1:18088` and `http://127.0.0.1:18090`.
- [ ] T017 [US1] Implement `risk-service/risk_service/results.py` (owner: Claude):
  - **Provenance builder**: every field in the `contracts/data-model.md` Provenance table, with `position_source` set to "TraderX account" plus a UTC `positions_read_at`, or "caller-supplied" plus `null`.
  - **Precedence**: the outcome order exactly as in `contracts/http-api.md` § Outcome precedence (steps 1–8).
  - **Envelope**: the RiskResult envelope (`outcome`, `message`, `provenance`, `account`, `current`, `missing_securities`). `current`, `track_record` and `verdict` are `null` for every outcome except `OK`, never 0.
  - **The `current` block**: `var_usd` = `var_forecasts(...)[N+1]`; `data_as_of`; `forecast_for`; positions sorted by security with `price` = the as-of close and `market_value` = quantity × price; `net_market_value`.
- [ ] T018 [US1] Implement `risk-service/risk_service/server.py` with `http.server.ThreadingHTTPServer`, bound to `0.0.0.0:18110` inside the container (publishing to the host is limited to 127.0.0.1 by T003) (owner: Claude). Routes:
  - `GET /health`;
  - `GET /api/v1/accounts`;
  - `GET /api/v1/risk/accounts/{accountId}`, which returns 400 `INVALID_REQUEST` when `accountId` is not a decimal integer;
  - `POST /api/v1/risk/positions`, which validates the body as in http-api.md § Caller-supplied body rules: a list, non-empty security strings, finite quantities, no duplicate security;
  - `GET /` serving the static files.

  HTTP status follows the outcome table in http-api.md. JSON is written with `json.dumps(..., allow_nan=False)`. Load prices once at startup, and exit non-zero if the checksum fails.
- [ ] T019 [US1] Build the page `risk-service/risk_service/static/index.html` and `static/app.js`, with no external assets (owner: Claude). It has:
  - a fixed top banner, "SYNTHETIC price history — not real market data", visible without scrolling;
  - an account picker filled from `/api/v1/accounts`;
  - the VaR figure to the cent, labelled "data as of 2026-11-13 close" and "forecast for 2026-11-16";
  - a positions table (security, quantity, price, market value) and the net value;
  - a distinct message for each non-OK outcome, with no VaR number shown.
- [ ] T020 [US1] Regression run after the shell is built: run the whole of `tests/unit` (`PYTHONPATH=risk-service python3 -m pytest tests/unit -q`, no `-k` filter), saving the output to `FEAT/validation/runs/us1-unit.txt` (owner: Claude). Failures are fixed only in `risk-service/`. A suspected test error goes to `FEAT/disputes.md`.

**Checkpoint**: the MVP works: an account's VaR with positions, prices and dates, and every error outcome.

---

## Phase 5: User Story 2 — See the backtest track record (Priority: P2)

**Goal**: 250 rows, each with the date, the forecast VaR made before that day, the realised P&L and
a breach flag. Covers FR-004, FR-005, FR-012 and M5.

**Independent Test**: account 22214 returns exactly 250 rows, for days 351 to 600, with
consecutive weekdays ending 2026-11-13. A row is flagged as a breach iff P&L < −VaR. V4 holds,
and V3 (the oracle) agrees within $0.01 with identical flags.

- [ ] T022 [US2] Add `track_record` to the OK result in `risk-service/risk_service/results.py` (owner: Claude): 250 items, each `{day, date: dates[t], forecast_var_usd, realised_pnl_usd, breach}`. Assert B = 250 for the service data.
- [ ] T023 [P] [US2] Add the track record to `risk-service/risk_service/static/app.js` and `index.html` (owner: Claude): a 250-row table with breach rows highlighted, and an inline SVG chart (realised P&L as bars, −VaR as a line, breach markers). If time runs short, the table alone satisfies FR-004 (research R10).
- [ ] T024 [US2] Regression run after the track record is wired in: run `PYTHONPATH=risk-service python3 -m pytest tests/unit tests/oracle -q`, saving the output to `FEAT/validation/runs/us2-unit-oracle.txt` (owner: Claude). The V2 band [1.24%, 1.54%] and the V3 agreement must pass; failures are fixed only in `risk-service/`.

**Checkpoint**: US1 and US2 both work on their own.

---

## Phase 6: User Story 3 — See a verdict on the model (Priority: P2)

**Goal**: breach count against 2.5 and 3.5, breach rate, Kupiec (LR, p-value, decision,
direction), Basel zone, and the fixed note. Covers FR-006, FR-007, FR-016, M6 and M7.

**Independent Test**: V5 table values to 4 decimal places (for example 0 breaches → LR 5.0252,
reject, too few, green; 7 → LR 5.4970, reject, too many, amber; 10 → red). The verdict note
matches http-api.md exactly.

- [ ] T026 [US3] Add `verdict` to the OK result in `risk-service/risk_service/results.py` with every field in the `contracts/data-model.md` Verdict table (owner: Claude): `observations` 250, `breaches`, `breach_rate`, `expected_breaches_nominal` 2.5, `expected_breaches_finite_sample` = 250 × `finite_sample_rate(250, 0.01)`, `finite_sample_rate`, `kupiec{lr, p_value, null_p 0.01, critical_value, reject_5pct, direction}`, `basel_zone`, and `note` = the exact text in http-api.md § Fixed verdict note.
- [ ] T027 [P] [US3] Add the verdict panel to `risk-service/risk_service/static/app.js` and `index.html` (owner: Claude). It shows the observed count next to "nominal expectation 2.5" and "finite-sample expectation 3.5", the rate, Kupiec LR, p-value, decision and direction, the zone shown in its colour, and the fixed note.
- [ ] T028 [US3] Regression run after the verdict is wired in: run the full `tests/unit`, saving the output to `FEAT/validation/runs/us3-unit.txt` (owner: Claude). V5 must pass.

---

## Phase 7: User Story 4 — See what every number is based on (Priority: P3)

**Goal**: full provenance on every response, errors included, and a synthetic label visible on the
page without scrolling. Covers FR-015, FR-017, FR-019 and SC-006.

**Independent Test**: every result type, including all 7 outcomes, carries all the provenance
fields with `synthetic: true` and seed 20261117. The banner is visible on page load.

- [ ] T029 [US4] Audit `risk-service/risk_service/results.py` and `server.py` so that every outcome path attaches the full provenance block (owner: Claude). That covers `INVALID_REQUEST`, `POSITIONS_UNAVAILABLE`, `ACCOUNT_NOT_FOUND`, `NO_OPEN_POSITIONS`, `MISSING_PRICE_HISTORY`, `ZERO_VOLATILITY` and `OK`, and `/api/v1/accounts` too. Fix any path that lacks it.
- [ ] T030 [P] [US4] Add a "Basis" panel to `risk-service/risk_service/static/app.js` and `index.html` (owner: Claude). It renders the provenance fields (seed, method, λ, pool, warm-up, confidence, horizon, quantile rule, as-of date, position source and read time, data SHA-256) under every result, including error results.

---

## Phase 8: Polish, stack run and submission gate

- [ ] T031 [P] Write `risk-service/README.md` (owner: Claude). It covers:
  - what the service computes, with the synthetic labelling;
  - the start, stop and test commands, copied from quickstart.md;
  - source and licence notes: the new code is under the repository licence, and the data is generated from seed 20261117 and anchored to the TraderX snapshot closes (finos/traderX@d6e7fe4, Apache-2.0);
  - every claim pointing to a test name or a file in `FEAT/validation/runs/`.
- [ ] T032 Start the stack (owner: Author). First stop the `traderx-state-008` stack from `/home/research/work/traderX-state-008` (ports collide). Then run `docker compose -f traderx/pricing-awareness-market-data/docker-compose.yml -f deploy/tau.override.yml --project-name traderx-tau up -d --build` and confirm that `curl -s http://127.0.0.1:18110/health` shows the data SHA-256. Claude never runs `up` or `down`.
- [ ] T033 Tier 2: `RISK_BASE_URL=http://127.0.0.1:18110 PYTHONPATH=risk-service python3 -m pytest tests/integration -q`, saving the output to `FEAT/validation/runs/integration.txt` (owner: Claude). V6, SC-006, SC-007 and SC-008 must pass. Failures are fixed only in `risk-service/` or `deploy/`.
- [ ] T034 [P] Measure SC-002: time each of `GET /api/v1/risk/accounts/22214`, `/52355` and `/44044` three times with `curl -w '%{time_total}'`, and record the results in `FEAT/validation/runs/latency.txt` (owner: Claude). The target is under 5 s each.
- [ ] T035 [P] Manual demo check (quickstart §5): take a screenshot of the page for account 22214, with the banner, VaR, dates, positions, track record, verdict and basis visible, and save it to `FEAT/validation/runs/demo-22214.png` (owner: Author). Record time-to-verdict for SC-001 (seconds from opening `http://127.0.0.1:18110/` to reading account 22214's verdict) in `FEAT/validation/runs/sc001-time.txt`.
- [ ] T036 Fill in `FEAT/traceability.md` (owner: Claude). Give one row per FR-001–FR-020 and SC-001–SC-008, with columns FR/SC → code location (`file:function`) → test (`tests/...::name`) → evidence file in `FEAT/validation/runs/`. A row with no passing test is marked "not yet verified" (Principle IV).
- [ ] T038 Commit `risk-service/`, `deploy/`, `FEAT/validation/runs/` (the evidence so far) and `FEAT/traceability.md` with DCO sign-off (owner: Author). Claude does not commit. This commit comes **before** T037, so that T037's clean-checkout start has the service code to build.
- [ ] T037 Run the submission gate on the T038 commit and save the output to `FEAT/validation/runs/gate.txt` (owner: Claude runs, Author checks). It runs:
  - `git diff fbdfb38 --stat -- traderx/`, which must be empty;
  - `sha256sum -c FEAT/validation/validator/tests.sha256`, all OK;
  - `git log --format='%h %s%n%(trailers:key=Assisted-by)' -- tests/`, where every listed commit is a validator import carrying `Assisted-by: qwen3-coder:30b via Ollama 0.40.3 (06c1097efce0)`;
  - `(cd FEAT/data && sha256sum -c SHA256SUMS)`;
  - the full tier 1 and tier 2 test runs, all passing;
  - quickstart §1–§7;
  - a clean-checkout start from the T038 commit, after T032's stack is stopped (ports collide): `git clone` the repository into a temporary folder, check out that commit, and run the documented compose command there (`docker compose -f traderx/pricing-awareness-market-data/docker-compose.yml -f deploy/tau.override.yml --project-name traderx-tau-clean up -d --build`). Check that `curl -s http://127.0.0.1:18110/health` shows the data SHA-256, then bring it down. The Author runs `up` and `down`; the output goes into `gate.txt`.
  - **If T037 finds a defect**, the fix is a new commit followed by a re-run of T037. Previous commits are never amended or force-pushed.
- [ ] T039 Commit `FEAT/validation/runs/gate.txt` and any final evidence with DCO sign-off, then push (owner: Author). This comes after T037 passes. Claude does not commit or push.

---

## Dependencies and execution order

```text
T000(done) → T000a (Author approves + commits tasks.md)
          → Phase 1 [T001, T002‖T003‖T004, T005]
          → T006 (Author reviews runner + prompts, approves the qwen run)
          → T007 → T008 → T008a (baseline capture) → T009 (one GPU, sequential; ≤2 retries each) → T010 (commit tests)
          → T011 (probe, fresh session) ‖ T012 (red run) ‖ T013 (dispute read)
          → T013a (commit probe, red run, disputes; push)
             └─ Phase 2 (T006–T013a) timeboxed to ~90 min
          → Core first (T014 depends on T013a) [T014 → T021 → T025 → T025a (core-offline.txt)]   ← cut line
          → US1 shell [T015‖T016 → T017 → T018 → T019 → T020]             ← MVP
          → US2 [T022 → T023 → T024]
          → US3 [T026 → T027 → T028]
          → US4 [T029 → T030]
          → Polish [T031‖T034‖T035, T032 → T033 → T036 → T038 (commit) → T037 (gate, incl. clean checkout of T038) → T039 (commit gate evidence, push)]
             └─ a defect found in T037 → new fix commit → re-run T037 (never amend or force-push)
```

- **The Core-first block** (T014, T021, T025) is all in `core.py`, so it runs in sequence. T025a
  gates everything after it.
- **US2 and US3 shell tasks** depend on the envelope (T017) and the server (T018). They are
  otherwise independent of each other.
- **US4** depends on T017 and T018, and audits all paths.
- **The same file in several stories** (`results.py`, `app.js`): stories run in order, not in
  parallel, for those files.

## Parallel opportunities

- **Phase 1**: T002, T003 and T004 (separate files).
- **After T010**: T011, T012 and T013 (probe, red run, read-only dispute review).
- **US1 shell**: T015 and T016 (prices.py and traderx_client.py), after T025a.
- **Core first**: no parallelism; T014, T021 and T025 share `core.py`.
- **UI tasks** T023, T027 and T030 can each run alongside that story's back-end task, because
  they are in different files.
- **Polish**: T031, T034 and T035.

## Implementation strategy

1. **Approval first**: T000a (tasks.md) and T006 (runner and prompts) are author gates. Nothing is
   implemented before T000a, and qwen does not run before T006.
2. **Phase 2 timebox**: at most 2 retries per round. Phase 2 as a whole (T006–T013) is timeboxed
   to about 90 minutes. If a round still fails after 2 retries, record it in `FEAT/disputes.md`
   with the reason, keep the last raw output, and continue. A missing round is reported as 'not
   yet verified' in traceability.md, never hidden.
3. **Core first (T014, T021, T025, T025a)**: the whole calculation, proved offline against V1, V2,
   V3 (offline part), V4 and V5. **This is the cut line if time runs out.** A verified offline
   core with its evidence file is worth more than a service shell on an unverified core.
4. **MVP = US1 shell** (T015–T020): the account page with VaR, positions, dates and every error
   outcome.
5. **US2 → US3**: wire the track record and verdict into the result and the page.
6. **US4**: mostly an audit, because provenance is built into the envelope from T017.
7. **Deadline guard** (2026-11-18 end of day ET): cut in this order — the SVG chart (T023
   fallback: table only), the screenshot (T035), then the shell phases from the end. Never cut
   Phase 2's evidence, T025a, T036 or T037 (Principles IV and V).
8. **Submission order**: T038 commits the code and evidence first. T037 then runs the gate on that
   commit, including the clean-checkout start, which can only build committed code. T039 commits
   `gate.txt` and pushes. A defect found by T037 is fixed in a new commit and T037 is run again.
   Earlier commits are never amended or force-pushed.

## Requirement → task map

| Requirement | Tasks |
|---|---|
| FR-001, FR-002, FR-003 | T014, T015, T016, T017, T019 |
| FR-004, FR-005 | T021, T022, T023 |
| FR-006, FR-007, FR-016 | T025, T026, T027; verified by T025a (V5) |
| FR-008, FR-009, FR-010, FR-011 | T016, T017, T018, T019 |
| FR-012 (no look-ahead) | T014, T021; verified by T025a, T020 and T024 (V4) |
| FR-013 (determinism) | T014, T018; verified by T033 (SC-008) |
| FR-014 (frozen data) | T000, T015 |
| FR-015 (provenance) | T017, T029, T030 |
| FR-017 (page) | T019, T023, T027, T030 |
| FR-018 (baseline unchanged) | T003, T008a; verified by T033 and T037 |
| FR-019 (structured API) | T018 |
| FR-020 (caller-supplied) | T017, T018 |
| Principle I (approval first) | T000a, T006 |
| Principle V (independence) | T001, T005, T006–T013, T037 |
| Principle IV (evidence) | T025a, T020, T024, T028, T033, T036, T037 |

## Notes

- Claude never creates, edits or deletes anything under `tests/`. T001 enforces this for the
  built-in Edit, Write and NotebookEdit tools. Coverage of Bash `cat`/`sed`/`tee` and `>` targets
  is expected, and is verified in T011, not assumed. T037 checks the result.
- Every run output is saved under `FEAT/validation/runs/`, so README claims can point to it.
- Commits are made only by the Author, with `Signed-off-by` (constitution, Project Constraints).
