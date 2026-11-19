# Implementation Plan: Portfolio Risk and VaR Track Record for TraderX Accounts

**Branch**: `001-portfolio-var-backtest` | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-portfolio-var-backtest/spec.md`

## Summary

**What it delivers**: a one-day 99% VaR for each TraderX account, a 250-day backtest track
record, and a verdict (Kupiec test and Basel zone). Every number is labelled as computed on frozen
synthetic price history.

**Technical approach**: one new service, `risk-service`, written in Python with only the standard
library.

- **Calculation**: a pure core module (`risk_service.core`) implements spec M2–M7 behind a
  documented calculation contract, which the validator's offline tests call.
- **Service shell**: a thin layer reads accounts and positions from TraderX with GET only, loads
  the checksum-verified CSV, applies the outcome precedence, and serves a JSON API and one static
  page on `127.0.0.1:18110`.
- **Deployment**: one new compose override file in this repository. No baseline file is edited.

## Technical Context

| Item | Choice |
|---|---|
| **Language/Version** | Python 3.10 in the container (`python:3.10-slim@sha256:2ee0fb87…a38ae`). Code is kept compatible with Python 3.9, which the host tests run on (3.9.7). |
| **Primary Dependencies** | Standard library only. Tests use pytest 8.x on the host. |
| **Storage** | None. Reads the frozen CSV (read-only mount) and TraderX over HTTP GET. |
| **Testing** | pytest. Tier 1 is offline (calculation contract and oracle); tier 2 is integration against the running stack. |
| **Target Platform** | A single Linux workstation, Docker Compose v2.24 or later, offline apart from image pulls. |
| **Project Type** | Web service plus a static page, added to an existing multi-service compose stack. |
| **Performance Goals** | Each result in under 5 s (SC-002). The expected cost is under 100 ms: about 350 sorts of 250 numbers per request. |
| **Constraints** | Deterministic (FR-013); no look-ahead (FR-012); 127.0.0.1 only; no CDN or pip; no baseline edits; deadline 2026-11-18 end of day ET. |
| **Scale/Scope** | 7 accounts, 20 tickers, 601 closes, a single local user. |

No NEEDS CLARIFICATION items remain; see [research.md](research.md) R1–R10.

## Constitution Check

*Gate: must pass before Phase 0; re-checked after Phase 1 (below).*

| Principle | How this plan complies | Status |
|---|---|---|
| **I. Spec-first** | The feature pack is `specs/001-portfolio-var-backtest/` (spec, plan, tasks). No implementation until the author approves `tasks.md`. One prior artifact, the data generator, is recorded under Complexity Tracking. | PASS, with one recorded deviation |
| **II. Additive delta** | **Baseline files touched: none.** All new code is in `risk-service/`, `deploy/` and `tests/`. The local-only port bindings and the new service are in the new file `deploy/tau.override.yml`, not in `traderx/`. Check: `git diff fbdfb38 --stat -- traderx/` is empty. Existing APIs are only called, with GET. | PASS |
| **III. Deterministic, offline** | Seed 20261117 and a frozen CSV with SHA-256 checked at startup. Standard library only, no pip or CDN. Fixed summation order, no parallelism. A locally present base image. | PASS |
| **IV. Evidence-gated** | `traceability.md` (FR → code → test) is created in T036. README claims point to test names or recorded outputs. | PASS (planned) |
| **V. Verifiable without trusting the author** | See Verification Design below: (a) V1 hand example; (b) V2 known-answer; (c) `tests/oracle/`, written by the validator model. Tolerances were pre-registered in the spec. The implementing side never edits `tests/`. The prompt and raw output are committed. | PASS (planned) |
| **VI. No look-ahead** | The calculation contract guarantees that VaRₜ depends only on x₁…x_{t−1}. V4 perturbs closes on or after t for t = 351, 600 and at least one more day. | PASS |
| **Constraints** | One new service plus a static page; no Angular change; 127.0.0.1 only; synthetic label on every response and on the page; DCO sign-off by the author only. | PASS |

### Verification design (Principle V; workflow gate 2)

| Spec item | Means | Tier | Owner |
|---|---|---|---|
| V1 hand example | `tests/unit`: calculation contract with `Params(0.94, 5, 2, 0.01)` | 1, offline | validator |
| V2 known answer | `tests/unit`: EWMA-consistent generator, 400 × 250, rate in [1.24%, 1.54%] | 1 | validator |
| V3 second implementation | `tests/oracle/`: an independent M2–M7 implementation from the spec only. Compared with the core on the frozen CSV for accounts 22214 and 52355 (as caller-supplied positions), and with the HTTP results in tier 2. Agreement within $0.01, identical flags. | 1 and 2 | validator |
| V4 no look-ahead | `tests/unit`: perturb closes ≥ t by ×U[0.5, 1.5]; VaRₜ bit-identical | 1 | validator |
| V5 Kupiec and Basel table | `tests/unit`: `kupiec`, `basel_zone` | 1 | validator |
| V6 outcomes | `tests/integration`: 99999, 44044, an unpriced ticker via POST | 2, stack | validator |
| FR-015, SC-006 provenance | `tests/integration`: every response type carries full provenance and `synthetic: true` | 2 | validator |
| SC-007 baseline | `tests/integration`: baseline GETs unchanged, and `git diff fbdfb38 -- traderx/` is empty | 2 | validator |

- **Validator model**: **qwen3-coder:30b** via local Ollama 0.40.3 (digest `06c1097e…0bca`).
  - Called through `validation/validator/run_validator.py` with `temperature 0`,
    `seed 20261117` and `num_ctx 65536`.
  - Three rounds: unit, oracle, integration (research R9).
  - Its inputs are exactly the canonical list in research.md R9, which is not repeated here. In
    short: the constitution, spec, and the four contracts (`calculation-api.md`, `http-api.md`,
    `data-model.md`, `test-harness.md`), plus the data file's metadata, checksums and format
    sample. It never sees quickstart.md, research.md, plan.md or `risk-service/`.
  - The author runs the runner, which writes only under `tests/`.
- **Evidence**:
  - every round's prompt, request and raw response are committed to
    `validation/validator/round-N/`;
  - disputes go to `disputes.md`.
- **Ordering**: the validator's tests are committed first and must fail against the empty
  implementation.
- **Settings probe** (research R11): six write paths (Write, Edit, Bash `>`, `>>`, `tee`,
  `sed -i`), each tried from the repository root and from `risk-service/`. All 12 must be
  refused. Recorded in `validation/validator/settings-probe.md`.
- **Enforcement** (research R11):
  - `.claude/settings.json` denies `Edit(/tests/**)`, which covers Edit, Write and NotebookEdit,
    plus Bash `cat`/`sed`/`tee` and `>` redirection;
  - the gap (writes from scripts, `cp`/`mv`) is closed at the submission gate by
    `validation/validator/tests.sha256` and
    `git log --format='%h %s%n%(trailers:key=Assisted-by)' -- tests/`. Every commit listed
    must carry `Assisted-by: qwen3-coder:30b via Ollama 0.40.3 (06c1097efce0)`.

## Project Structure

### Documentation (this feature)

```text
specs/001-portfolio-var-backtest/
├── spec.md, input.md
├── plan.md                 # this file
├── research.md             # Phase 0
├── quickstart.md           # Phase 1 (run guide for people; not a validator input)
├── contracts/              # validator inputs (with spec.md and the constitution)
│   ├── calculation-api.md  # pure-function contract (tier-1 tests, oracle)
│   ├── http-api.md         # JSON API, outcomes, provenance, page
│   ├── data-model.md       # entities and fields (moved here from the feature root)
│   └── test-harness.md     # paths, env vars, commands, tiers, file formats; no expected values
├── data/                   # frozen synthetic history (FR-014) + generator + SHA256SUMS
├── validation/
│   ├── prestudy_coverage.py
│   └── validator/          # validator prompt + raw output (Principle V)
├── disputes.md             # created on first dispute
├── traceability.md         # FR → code → test (Principle IV), filled during implement
└── tasks.md                # /speckit-tasks
```

### Source Code (repository root)

```text
risk-service/                   # NEW, implementing side (Claude)
├── Dockerfile                  # FROM python:3.10-slim@sha256:2ee0…; no pip install
├── README.md                   # run, synthetic labelling, source/licence note
└── risk_service/
    ├── __init__.py
    ├── core.py                 # M2–M7 pure functions (contracts/calculation-api.md)
    ├── prices.py               # load CSV, verify SHA-256, dates, as-of / forecast-for
    ├── traderx_client.py       # GET account + positions, 5 s timeout
    ├── results.py              # outcome precedence (R8), provenance, RiskResult assembly
    ├── server.py               # ThreadingHTTPServer, routes, JSON encoding
    └── static/
        ├── index.html          # banner, account picker, VaR, positions, track record, verdict
        └── app.js              # fetch + render table and inline SVG chart

.claude/
└── settings.json               # NEW: permissions.deny ["Edit(/tests/**)"] (R11)

deploy/
└── tau.override.yml            # NEW: 127.0.0.1 bindings for all baseline services + risk-service

tests/                          # NEW, validator-owned (implementing side MUST NOT edit)
├── unit/                       # tier 1: V1, V2, V4, V5, contract behaviour
├── oracle/                     # tier 1/2: independent implementation (V3)
└── integration/                # tier 2: HTTP outcomes, provenance, baseline unchanged

traderx/                        # BASELINE, unchanged
```

**Structure decision**: one new service folder at the repository root, kept apart from the
`traderx/` baseline so that the Principle II diff stays clean. Tests sit at the root under
`tests/`, which the constitution reserves for the validator.

## Baseline files touched (Principle II)

**None.** The new `.claude/settings.json` is tool configuration, not part of the TraderX baseline.
All wiring is in the new `deploy/tau.override.yml`, which:
- binds every baseline service to 127.0.0.1 with `ports: !override`;
- adds `risk-service`, with a build context of `../../risk-service` and a read-only volume of
  `../../specs/001-portfolio-var-backtest/data`. Both paths resolve against the first compose
  file's folder; checked with `docker compose config`.

## Complexity Tracking

| Deviation | Why needed | Simpler alternative rejected because |
|---|---|---|
| The synthetic-data generator and CSV (`data/`) were written and committed before `tasks.md` existed (Principle I) | FR-014 and Clarification 3 make the data a fixed input that must exist before the validator starts. The author asked for it directly and reviewed and committed it. | If the implementation produced the data, the implementing side would control the test input and the validator's tests could not run first. `tasks.md` will list it as already done (T000) for traceability. |
| `start-env.sh` is not the start command; a direct `docker compose` command is used | The snapshot's start script needs `pipeline/` and `generated/`, which do not exist here (research R3) | Restoring the pipeline is upstream generation work and out of scope |

## Post-design Constitution re-check

Re-checked after writing contracts/ (including contracts/data-model.md and
contracts/test-harness.md) and quickstart.md. Nothing changed:

- no baseline edits were introduced;
- every V1–V6 item maps to a test location and owner;
- all external calls are GET;
- no new dependencies were added;
- the validator is fixed as qwen3-coder:30b (a different model family, run locally);
- the "no edits to `tests/`" rule is now also enforced by `.claude/settings.json`, with checksum
  evidence covering the gap that setting leaves.

**Result: PASS.**
