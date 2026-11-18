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
