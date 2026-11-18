# Research: 001 Portfolio Risk and VaR Track Record

All Technical Context unknowns are resolved below. The facts were checked against the repository
and the running local stack on 2026-11-18.

## R1. Runtime and dependencies

- **Decision**: Python using only the standard library (`http.server`, `json`, `csv`, `math`,
  `hashlib`, `urllib`). The code stays compatible with Python 3.9, because the host has 3.9.7. The
  container image is `python:3.10-slim`
  (`python@sha256:2ee0fb8794bf82af1b2db168ada5869b4c27d17720dd3b155b56c111fb4a38ae`), which is
  already pulled locally.
- **Rationale**:
  - Constitution III allows network access only for pulling container images, so a `pip install`
    during the image build would break it.
  - The Kupiec p-value needs only `math.erfc`: for χ²(1), the upper tail is erfc(√(LR/2)).
  - The data is 600 × 20 values and the per-request work is about 350 sorts of 250 numbers, so
    no numeric library is needed.
- **Alternatives considered**:
  - FastAPI or Flask: needs a pip install and adds nothing at this size.
  - numpy: makes floating-point results depend on the numpy version, and is not needed.
  - Java or Spring, to match the TraderX services: slower to build before the deadline, and the
    validator works more easily against a Python calculation contract.

## R2. Where the service runs and how it is reached

- **Decision**: a new compose service `risk-service` on port 18110, bound to `127.0.0.1`. It is
  added by a new override file, `deploy/tau.override.yml`. The page and the JSON API are served
  by the same service at `http://127.0.0.1:18110/`. The ingress is not changed.
- **Rationale**:
  - No baseline file changes, so `git diff fbdfb38 --stat -- traderx/` stays empty.
  - FR-017 asks for a page outside the TraderX front end, and this provides it.
  - The page and the API share an origin, so CORS configuration is not needed.
- **Alternatives considered**: an nginx route `/risk-service/`. That would edit
  `traderx/ingress/nginx.traderx.conf.template`, a baseline file, for little gain.

## R3. Starting from a clean checkout

**Findings**:
- `traderx/start-env.sh` hands off to `scripts/start-state-008-…-generated.sh`. That script calls
  `pipeline/generate-state.sh` and expects a `generated/` tree, and neither exists in this
  snapshot.
- The stack currently running (project `traderx-state-008`) was started from another checkout,
  `/home/research/work/traderX-state-008`. It uses an override outside this repository:
  `/home/research/work/traderx-local-only.override.yml`, with `ports: !override` bound to
  127.0.0.1.
- That checkout's `pricing-awareness-market-data/` folder is byte-identical to this one
  (`diff -rq` shows no differences).

**Decision**: start the stack directly with compose:
```
docker compose -f traderx/pricing-awareness-market-data/docker-compose.yml \
               -f deploy/tau.override.yml --project-name traderx-tau up -d --build
```
The override file:
- copies the 127.0.0.1 `!override` port bindings for all 19 baseline services, so the
  constitution's local-only rule lives in this repository;
- adds `risk-service`.

**Check**: `docker compose … config` (no `up`) shows that relative paths in a second `-f` file
resolve against the first file's folder. So `../../risk-service` and
`../../specs/001-portfolio-var-backtest/data` point to the repository root (checked 2026-11-18).

**Constraint**: only one TraderX stack can hold ports 8080, 18083–18100 and so on at a time. The
author must stop the `traderx-state-008` stack before starting `traderx-tau`. That is an
author-run step, never automated by the AI.

**Alternatives considered**: restoring the pipeline scripts. Out of scope; they belong to
upstream generation.

## R4. Reading accounts and positions from TraderX

Behaviour seen on the running stack:

| Call | Result |
|---|---|
| `GET account-service:18088/account/{id}` | 200 `{"id":22214,"displayName":"Test Account 20"}`; **404** with text `Account with id 99999 not found` |
| `GET position-service:18090/positions/{accountId}` | 200 list of `{accountId, security, quantity, averageCostBasis, updated}`; **200 `[]` for an unknown account** |
| `GET account-service:18088/account/` | 200 list of 7 accounts |

**Decision**:
- Look the account up first. A 404 means `ACCOUNT_NOT_FOUND`.
- Then read the positions.
- Any connection error, timeout (5 s) or 5xx from either call means `POSITIONS_UNAVAILABLE`.
- Both calls are GET only, so nothing is written to TraderX.

**Rationale**: the position API cannot tell an unknown account from an empty one, so FR-008
needs the account service.

## R5. Data file handling

- **Decision**:
  - The compose service mounts `specs/001-portfolio-var-backtest/data/` read-only at `/data`.
    Outside a container, the path is set with `RISK_DATA_DIR`.
  - At startup the service computes the CSV's SHA-256. It refuses to start unless the hash equals
    the value in spec M1: `9ea2eab1…0718ce3`.
  - Prices are parsed with `float()` from the 4-decimal text. The rounded values in the file are
    the prices (M1 Precision).
- **Rationale**: FR-014 says the file is authoritative, read only, and never regenerated. The
  checksum check makes a silent change impossible.

## R6. Numerical determinism

- **Decision**:
  - Plain Python floats (IEEE-754 double).
  - P&L is summed over positions in ascending security-symbol order.
  - The quantile is taken from `sorted()` of the pool.
  - EWMA is computed by the M3 recursion in day order.
  - JSON numbers are written with Python `repr`, which round-trips exactly.
  - No parallelism and no clock-dependent logic. The only exception is `positions_read_at`,
    which is provenance and not a numeric result.
- **Rationale**: SC-008 (byte-identical numbers) and FR-013. The agreement tolerance with the
  independent implementation ($0.01) is far wider than any difference from summation order.

## R7. Kupiec details

- LR follows M6 with 0·ln 0 = 0.
- p-value = erfc(√(LR/2)).
- Reject when LR > 3.841458820694124, the χ²(1) 95% point.
- Direction is reported only on rejection: `too_many` if x > 2.5, `too_few` if x < 2.5.
- Checked against spec V5 for 0, 1, 2, 3, 4, 5, 6, 7 and 10 breaches, using scipy during the
  pre-study. The implementation itself does not use scipy.

## R8. Outcome precedence (when more than one could apply)

- **Decision**: the order below.
- **Where it is normative**: `contracts/http-api.md` § Outcome precedence, because the
  validator does not receive this research file. This section only records the reasoning; if the
  two ever differ, the contract wins.

Checks run in this order, and the first match wins:

1. `INVALID_REQUEST` (400): a caller-supplied body is malformed, a quantity is not finite, or a
   security is duplicated.
2. `POSITIONS_UNAVAILABLE` (503): TraderX account or position lookup failed (account path only).
3. `ACCOUNT_NOT_FOUND` (404): account path only.
4. Positions with quantity 0 are dropped.
5. `NO_OPEN_POSITIONS` (200): nothing left.
6. `MISSING_PRICE_HISTORY` (422): lists **every** remaining security not in the CSV, sorted. A
   zero-quantity position in an unpriced ticker was dropped in step 4 and is not reported.
7. `ZERO_VOLATILITY` (422): exactly when σ²_{W+1} = 0, that is, every warm-up P&L is 0. If
   σ²_{W+1} > 0, every later σ² is ≥ λ·σ²ₛ > 0, so no other trigger is possible.
8. `OK` (200).

## R9. Validator model and evidence locations (constitution V)

- **Who validates**: **qwen3-coder:30b**, served locally by Ollama 0.40.3. Details:
  - digest `06c1097efce0431c2045fe7b2e5108366e43bee1b4603a7aded8f21689e90bca`;
  - Q4_K_M quantisation, 30.5B parameters (MoE), Apache-2.0 licence;
  - it is a different model family from Claude, which writes the implementation, so constitution
    V is satisfied;
  - it runs on the workstation, so constitution III (offline) is satisfied.
- **How it is called**:
  - The Ollama HTTP API at `http://127.0.0.1:11434/api/chat`, called by a small runner script
    (`validation/validator/run_validator.py`, standard library only).
  - Fixed options: `temperature 0`, `seed 20261117` and **`num_ctx 65536`**. Ollama's default
    context window is a few thousand tokens. Without this setting the spec and contracts would be
    cut off silently, and qwen would write tests from part of the spec.
  - The runner stops with an error if the prompt's token count (`prompt_eval_count` in the
    response) comes close to `num_ctx`.
- **Three separate rounds**, one prompt each, which keeps each answer within a 30B model's
  reliable output length:
  1. `tests/unit/`: V1, V2, V4, V5 and calculation-contract behaviour;
  2. `tests/oracle/`: the independent M2–M7 implementation and its comparison test (V3);
  3. `tests/integration/`: V6, provenance, SC-007 and SC-008, run over HTTP.
- **Getting the files out**:
  - qwen is told to emit every file as a fenced block whose info string is
    `python file=tests/<path>`.
  - The runner writes each block verbatim to that path. It accepts only paths under `tests/`
    and stops if any other path appears.
  - The author runs the runner, not Claude. That keeps it consistent with the settings deny rule
    (R11).
- **Recorded for every round**: the exact prompt, the request JSON (model, digest, options), the
  raw response JSON, and the list of extracted files with their SHA-256. All are saved in
  `validation/validator/round-N/`.
- **Re-runs**: if a round produces broken or incomplete code, the author may re-run it with a
  feedback note. The note is saved too, as `round-N/retry-M/`. Neither Claude nor the author
  edits the generated test files by hand. A wrong test goes to `disputes.md`, and the author
  decides it.
- **Validator inputs (canonical list; plan.md refers here and does not repeat it)**:
  1. `.specify/memory/constitution.md`
  2. `specs/001-portfolio-var-backtest/spec.md`
  3. `specs/001-portfolio-var-backtest/contracts/calculation-api.md`
  4. `specs/001-portfolio-var-backtest/contracts/http-api.md`
  5. `specs/001-portfolio-var-backtest/data-model.md`
  6. `specs/001-portfolio-var-backtest/quickstart.md`
  7. From `data/`, the full text of `synthetic_prices_seed20261117.meta.json` and `SHA256SUMS`,
     plus the CSV's header line and its first and last 3 rows (to show the format). The complete
     601-row CSV is not pasted into the prompt. The tests read it from its path when they run.
- **Not given to the validator**: `research.md`, `plan.md`, `tasks.md`, anything under
  `risk-service/`, `data/generate_synthetic_prices.py`, and `validation/prestudy_coverage.py`.
  This is why every rule the tests depend on, including the outcome precedence (R8), must be in
  the spec, the contracts, the data model or the quickstart.
- **Enforcement**: `run_validator.py` builds each prompt from exactly this list. It writes the
  list of paths and their SHA-256 values into every round's `request.json`, so a reviewer can
  confirm that nothing else was sent.
- **Validator outputs**:
  - `tests/` (all test code);
  - `tests/oracle/` (the independent implementation, V3);
  - the prompt and raw output, committed in `specs/001-portfolio-var-backtest/validation/validator/`.
- **Disputes**: `specs/001-portfolio-var-backtest/disputes.md`, decided by the author.

## R11. Enforcing "the implementing side does not edit `tests/`"

- **Decision**: add a task that creates the project settings file `.claude/settings.json` with
  `{"permissions": {"deny": ["Edit(/tests/**)"]}}`.
  - The rule is then enforced by configuration, not only by the constitution.
  - Settings source: Claude Code permissions docs (code.claude.com/docs/en/permissions), read on
    2026-11-18.
- **Why this pattern**:
  - A leading `/` anchors the pattern to the session's primary working directory, the repository
    root. A bare `tests/**` is relative to the current directory and stops matching when the
    shell moves into a subfolder, which has happened in this session.
  - An `Edit(...)` rule applies to every built-in file-editing tool: Edit, Write and NotebookEdit.
    A `Write(path)` rule is never matched, so it is not used.
  - Deny rules are also checked against Bash file commands Claude Code recognises (`cat`, `sed`,
    `tee` and so on) and against `>` redirection targets.
- **Known gap**: the deny does not cover writes made by a Python or Node process that opens files
  itself, or commands such as `cp` and `mv` that the docs do not list.
- **Closing the gap with evidence instead of more tooling**:
  - When the validator's tests are committed, the author records a checksum file
    `validation/validator/tests.sha256` covering every file under `tests/`.
  - Every validator-import commit carries the trailer
    `Assisted-by: qwen3-coder:30b via Ollama 0.40.3 (06c1097efce0)`, together with the author's
    DCO `Signed-off-by`.
  - The submission gate checks the checksum file with `sha256sum -c`.
  - It then runs `git log --format='%h %s%n%(trailers:key=Assisted-by)' -- tests/`. Every
    commit listed must be a validator import carrying that trailer.
  - An optional PreToolUse hook that inspects Bash command text for `tests/` was rejected because
    it adds tooling without adding evidence.
- **Verification task (settings probe)**: run after the validator's tests are committed, so that
  `tests/` holds files that can be edited. Each attempt runs in a Claude session started at the
  repository root, once with the shell at the root and once after `cd risk-service`. From
  `risk-service/`, paths are written as `../tests/…`.

  | # | Path | Attempt | Expected |
  |---|---|---|---|
  | P1 | Write tool | create `tests/_probe.py` | refused |
  | P2 | Edit tool | change one line of an existing `tests/unit/*.py` | refused |
  | P3 | Bash, redirection | `echo x > tests/_probe.py` | refused |
  | P4 | Bash, append | `echo x >> tests/unit/<existing>.py` | refused |
  | P5 | Bash, `tee` | `echo x \| tee tests/_probe.py` | refused |
  | P6 | Bash, `sed -i` | `sed -i 's/a/a/' tests/unit/<existing>.py` | refused |

  - That is 12 attempts (6 paths × 2 working directories). The prompt, tool call and refusal
    text of each are recorded in `validation/validator/settings-probe.md`.
  - **Pass**: all 12 are refused, `git status --porcelain -- tests/` is empty afterwards, and
    `sha256sum -c validation/validator/tests.sha256` still passes.
  - **On failure**: any attempt that succeeds is a recorded finding in `disputes.md`. The
    file is restored with `git checkout -- tests/` by the author, and the rule is fixed before
    implementation starts.
  - **Not probed on purpose**: writes from a Python subprocess, and `cp`/`mv`. Those are the
    documented gap. They are covered by the checksum and `git log` evidence, and testing them
    would mean breaking the rule for real.

## R10. Track record presentation

- **Decision**: a table with all 250 rows, breach rows highlighted, plus an inline SVG chart. The
  chart shows realised P&L as bars and −VaR as a line, with breach markers. It is plain
  JavaScript with no CDN.
- **Rationale**: constitution III requires offline operation. A risk manager reads the chart in
  seconds, which supports SC-001.
- **Fallback**: if time runs short, the table alone satisfies FR-004.
