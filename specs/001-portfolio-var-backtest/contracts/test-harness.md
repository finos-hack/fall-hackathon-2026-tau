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
