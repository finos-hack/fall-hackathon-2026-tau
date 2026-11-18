# Disputes and deviations — feature 001

Each entry: what happened, the evidence, and the Author's decision. Drafted by Claude (the
implementing side) from its read-only reviews; decided by the Author. Nothing here changes a
pre-registered expectation in spec.md.

## D-001 — Validator round 1 with qwen3-coder:30b: test errors after two retries (T007)

- **Evidence**: `validation/validator/round-1/` (first run, retry-1, retry-2), committed in fb1ece2.
- First run: 8 conflicts with the spec, among them numpy imported (standard library only), the V1
  variant changed C₇ instead of C₈, the V2 generator ignored the M3 seed, and V4 compared the
  day-N+1 forecast instead of VaRₜ, with a tolerance instead of bit-for-bit equality.
- Retry 1 fixed 4 of them. Still wrong: the V1 variant (changed C₇ again), V2 (a name used before
  assignment, so it could never run; seed (Σx)²/W instead of Σx²/W), V4 tolerance 1e-10, no
  "Open questions" section.
- Retry 2 was rejected by the runner: the answer also wrote `tests/oracle/oracle_implementation.py`,
  outside round 1's folder, and imported numpy again.
- **Decision (Author, 2026-11-18)**: superseded by D-003. The Qwen output is kept as a record
  only; no Qwen-written test is in `tests/`.

## D-002 — Validator round 2 with qwen3-coder:30b: no usable oracle after two retries (T008)

- **Evidence**: `validation/validator/round-2/` (first run, retry-1, retry-2), committed in fb1ece2.
- First run: oracle failed with NameError; pool held n−1 residuals; σ_{N+1} missing, so current VaR
  0 and 249 backtest rows; Kupiec p-value via scipy and halved; package import failed under pytest;
  account 52355 given invented positions (see D-004).
- Retry 1: no forecasts at all (V1 returned `{}`, 0 backtest rows); kupiec raised
  UnboundLocalError; the comparison with `risk_service.core` was missing entirely.
- Retry 2: the test file had no assertions; `var_forecasts` used an undefined name; edge rule
  `k+1 >= n`; p-value `1 − erfc(√(LR/2))/2` (0.919 for 5 breaches, spec 0.1619); kupiec(0) raised.
- **Decision (Author, 2026-11-18)**: round 2 failed under the T008 rule. See D-003.

## D-003 — Validator model changed to gpt-5.6-terra via codex-cli 0.151.0 (deviation from plan R9)

- **Why**: D-001 and D-002. qwen3-coder:30b repeated the same errors despite review notes (pool of
  n−1 twice, numpy three times, "Open questions" missing in 6 of 6 answers).
- **What stayed the same**: prompt files, canonical input list with SHA-256s, acceptance rules
  (fenced files only, folder and prefix checks, folder replacement, files.sha256), the 2-retry limit
  per round, and spec V3's requirement that the validator is a different AI model from the
  implementer (Anthropic implements; OpenAI validates).
- **Isolation controls added** (run_validator.py `--provider codex`, fb1ece2): one `codex exec`
  call from a new empty temporary folder, read-only sandbox, user config, rules and session history
  ignored; the JSON event log is saved and the run is rejected if it shows any item other than the
  model's messages and reasoning. All accepted runs show `item_types: ["agent_message"]` only.
- **Results**: round 1 accepted on the first run; round 2 accepted on the first run; round 3
  accepted on retry 2 (D-006). Records: `validation/validator/codex/`. Tests committed in 58abb74.
- **Decision (Author, 2026-11-18, about 17:30 ET)**: approved.

## D-004 — Spec gap: account 52355's seeded position was not stated

- spec.md named accounts 22214 and 52355 for V3 but listed only 22214's positions. 52355's position
  (BAC −2400) was in `traderx/database/initialSchema.sql` and `baseline-before.json`, neither of
  which is a validator input, so the round 2 validator had no source for it.
- **Fix**: spec amendment, commit dfd5bef (Clarifications, and V3's first sentence). No expected
  value changed.

## D-005 — Contract ambiguity: `positions_read_at` per outcome

- `contracts/data-model.md` said "null … when nothing was read", which left 44044 (position lookup
  returned an empty list) and 99999 (account 404) open to two readings.
- **Fix**: clarified per outcome before the tests were committed, commit 809bbec.

## D-006 — Codex round 3: two test errors fixed by retries

- First run: the provenance helper compared `positions_read_at` with `is True`, so every correct OK
  response on the account path would fail. Retry 1 fixed it (and applied D-005).
- Retry 1: the SC-007 test parsed every TraderX body as JSON; `/account-service/account/99999`
  answers `text/plain`, and test-harness.md says such bodies are stored as strings. Retry 2 fixed
  it. Verified against the live 404 response.
- **Decision (Author)**: retry 2 accepted.

## D-007 — Coverage gaps in the accepted tests (not test errors)

The validator listed these under "Open questions"; they are true gaps in the harness:

- `POSITIONS_UNAVAILABLE` (503) over HTTP: no fault-injection mechanism in the harness.
- `ZERO_VOLATILITY` (422) over HTTP: no priced ticker in the frozen file has zero warm-up P&L.
  Covered at unit level by `ZeroVolatilityError`.
- SC-008 "two clean starts": tested as two requests to one running service.
- Not tested: `GET /health`, `GET /api/v1/accounts`, the page at `GET /`.
- **Plan**: checked by hand at T037 (stop TraderX and expect 503; restart the service and compare
  the result blocks byte for byte; curl the three endpoints) and recorded in the gate evidence.

## D-008 — T013 spec-conformance read of the committed tests

- Every assertion in `tests/` was read against spec.md and contracts/. No test contradicts them.
- Observations, not disputes: some unit tests use exact float equality, so the implementation must
  follow the contract's formula order and use `math.sqrt`; one test assumes `var_forecasts` keys are
  in ascending order; V4 uses deterministic synthetic closes instead of the published file (V4 does
  not name a data set).
- **Disclosure**: while reviewing round 2, Claude ran the oracle on the published history and saw
  its current VaR and breach count for both seeded accounts. The implementation is written from
  spec.md and contracts/ only; agreement is checked by the tests, not by matching those numbers.

## D-009 — Process slips

- T010 did not include `validation/validator/tests.sha256`; it was added in 0ddb328, before T011.
- The README summary (e9918ff on the feature branch) was cherry-picked to `main` as 443116e so that
  reviewers of the default branch see it.
- T010's trailer names the codex validator instead of the Qwen trailer in tasks.md, as a
  consequence of D-003.
- Commit 58abb74 carries `Co-Authored-By: Claude Haiku 5.5`; the session model was Opus 5.5. The
  commit is pushed and is not rewritten.

## D-010 — T011 settings probe: passed, with one limit on what it proves

- **Evidence**: `validation/validator/settings-probe.md`. A new session started 2026-11-18
  18:06:30 EST, after `.claude/settings.json` was committed (fb9028c, 12:40:27). A first attempt in
  a session started on 2026-11-17 was stopped before any probe ran, because that session predates
  the settings.
- **Result**: all 12 attempts (P1–P6, from the root and from `risk-service/`) refused;
  `git status --porcelain -- tests/` empty; `sha256sum -c tests.sha256` all OK. This meets T011's
  pass criterion.
- **Limit**: the session ran in auto mode. The Write and Edit refusals name the permission
  settings, so the `Edit(/tests/**)` rule is shown to block them. The four Bash refusals (`>`, `>>`,
  `tee`, `sed -i`) do not say which rule denied them, so this run does not prove that
  `Edit(/tests/**)` alone blocks Bash writes (research R11 expected it to; that expectation stays
  unverified).
- **Other notes**: before P2 the session read the first 5 lines of the target file, because the
  Edit tool refuses an unread file before it checks permissions. From `risk-service/`, Write and
  Edit used absolute paths containing `/../tests/` (those tools accept only absolute paths); the
  Bash probes used the literal relative `../tests/` paths.
- **Why the limit is acceptable**: the integrity of `tests/` does not rest on the deny rule alone.
  `tests.sha256` (0ddb328) is checked again at the gate (T037), and any change under `tests/` would
  show in git history after 58abb74.
- **Decision (Author)**: <accept as passed with this limit recorded >

## D-011 — Correction to D-007: the accepted tests do cover ZERO_VOLATILITY over HTTP

- D-007 was written from the review of round 3 retry 1. The accepted retry 2
  (`tests/integration/test_integration_risk_http.py`) reaches `ZERO_VOLATILITY` over HTTP by
  posting the smallest subnormal positive quantity for a ticker whose warm-up P&L then rounds to
  exactly zero, and also asserts the exact verdict note (FR-016), `data_as_of`, `forecast_for` and
  every row date.
- The remaining HTTP gap is `POSITIONS_UNAVAILABLE` (503), and SC-008 across two clean starts.
  Both are checked by hand at T037.
- Recorded by Claude during implementation, 2026-11-18. `traceability.md` reflects the corrected
  coverage.

## D-012 — The T010 commit's Assisted-by line is not a git trailer

- Commit 58abb74 (the only commit touching `tests/`) carries `Assisted-by: gpt-5.6-terra via
  codex-cli 0.151.0` in its message, but as a separate paragraph: the commit command Claude
  supplied used one `-m` per line. Git therefore does not parse it as a trailer, and
  `git log --format='%(trailers:key=Assisted-by)'` prints nothing for it.
- The commit is pushed and is not rewritten. The gate (T037) checks the message body for the
  `Assisted-by:` line in addition to the trailer, and records both results.
