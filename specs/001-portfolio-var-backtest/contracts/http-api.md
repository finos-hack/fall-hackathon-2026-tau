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
