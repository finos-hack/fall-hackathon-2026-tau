# Quickstart and Validation Guide: 001 Portfolio VaR

This guide lists runnable checks only. Expected values come from spec.md (V1–V6) and from
contracts/. All commands run from the repository root.

## 0. Prerequisites

- Docker Engine with the Compose plugin v2.24 or later (`!override` support). Checked with v2.35.1.
- Python 3.9 or later and pytest on the host.
- Image `python:3.10-slim` already pulled. No other network access is needed.
- **Author step:** no other TraderX stack may be holding the ports. If the `traderx-state-008`
  stack from the other checkout is running, the author stops it from that checkout.

## 1. Data integrity (no stack needed)

```bash
(cd specs/001-portfolio-var-backtest/data && sha256sum -c SHA256SUMS)
python3 specs/001-portfolio-var-backtest/data/generate_synthetic_prices.py --check   # prints MATCH
```

## 2. Tier 1: offline tests (no stack needed)

```bash
PYTHONPATH=risk-service python3 -m pytest tests/unit tests/oracle -q
```

| Check | Expected |
|---|---|
| V1 hand example | VaR₈ = 33.3085 ± 0.0001; not a breach; with C₈ = 92 it is a breach and VaR₈ is unchanged |
| V2 known answer | pooled breach rate in [1.24%, 1.54%] over 400 × 250 forecasts |
| V4 perturbation | VaRₜ bit-identical for t ∈ {351, 600, plus ≥1 more} |
| V5 Kupiec and Basel | table values to 4 decimal places; zones green, amber, red |
| V3 oracle vs core | accounts 22214 and 52355 as caller-supplied positions: every VaR within $0.01, breach flags identical |

Before `/speckit-implement`, the same command must **fail**: the package does not exist yet, so
imports fail (constitution workflow, step 4).

## 3. Start the stack

```bash
docker compose -f traderx/pricing-awareness-market-data/docker-compose.yml \
               -f deploy/tau.override.yml --project-name traderx-tau up -d --build
curl -s http://127.0.0.1:18110/health           # {"status":"ok","data_sha256":"9ea2…","synthetic":true}
```

## 4. Tier 2: integration tests (stack running)

```bash
RISK_BASE_URL=http://127.0.0.1:18110 PYTHONPATH=risk-service python3 -m pytest tests/integration -q
```

| Check | Expected |
|---|---|
| `GET /api/v1/risk/accounts/22214` | 200 `OK`; 3 positions with as-of prices C 58.6, IBM 187.4, MS 91.1; 250 rows; verdict fields; full provenance |
| Same call, POST with the same 3 positions | identical `current`, `track_record` and `verdict`; `position_source` is `caller-supplied` |
| `GET …/accounts/99999` | 404 `ACCOUNT_NOT_FOUND`, no VaR |
| `GET …/accounts/44044` | 200 `NO_OPEN_POSITIONS`, no VaR |
| POST `[{"security":"AAPL","quantity":10},{"security":"ZZZZ","quantity":5}]` | 422 `MISSING_PRICE_HISTORY`, `missing_securities: ["ZZZZ"]` |
| Two runs of the same request | numeric fields byte-identical (SC-008) |
| Baseline lookups (`/account/22214`, `/positions/22214`, `/account/`) on 18088 and 18090 | same responses as the baseline stack (SC-007) |

Live positions can change when trades are booked. Numeric comparisons therefore use the
caller-supplied path with the seeded positions. The account path is checked for shape, outcome
and consistency with its own position list.

## 5. Manual demo

Open `http://127.0.0.1:18110/` and pick "Test Account 20 (22214)". You should see:

- the SYNTHETIC banner, without scrolling;
- VaR labelled "data as of 2026-11-13 close" and "forecast for 2026-11-16";
- the positions table;
- the 250-row track record with breach rows marked, and the chart;
- the verdict with 2.5 and 3.5 next to the observed count, Kupiec, the zone, and the fixed note.

## 6. Validator independence (Principle V)

```bash
sha256sum -c specs/001-portfolio-var-backtest/validation/validator/tests.sha256   # every tests/ file OK
git log --format='%h %s%n%(trailers:key=Assisted-by)' -- tests/
```

Expected:
- every line of the checksum check says OK;
- every commit that touches `tests/` is a validator import, and carries the trailer
  `Assisted-by: qwen3-coder:30b via Ollama 0.40.3 (06c1097efce0)`;
- no commit touching `tests/` lacks that trailer or names any other model;
- `validation/validator/settings-probe.md` records that every write attempt in the probe was
  refused: 6 write paths (Write, Edit, Bash `>`, `>>`, `tee`, `sed -i`), each tried from the
  repository root and from `risk-service/`, 12 attempts in all.

## 7. Baseline untouched (Principle II)

```bash
git diff fbdfb38 --stat -- traderx/      # expected: empty
```

## 8. Stop

```bash
docker compose -f traderx/pricing-awareness-market-data/docker-compose.yml \
               -f deploy/tau.override.yml --project-name traderx-tau down
```
