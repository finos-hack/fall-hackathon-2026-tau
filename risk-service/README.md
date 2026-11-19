# risk-service — one-day 99% VaR and backtest for TraderX accounts

> **All figures are computed on SYNTHETIC price history (seed 20261117). It is not real market
> data.** Every response says so in its `provenance` block, and the page shows a banner.

## What it computes

For a TraderX account (or a caller-supplied position list) the service returns:

- **Current VaR**: the one-day 99% VaR in dollars of today's positions, by filtered historical
  simulation on portfolio dollar P&L: EWMA volatility (λ = 0.94, warm-up 100), a 250-day pool of
  standardized residuals, and the linearly interpolated quantile at position (n−1)p. Labelled
  "data as of 2026-11-13 close" and "forecast for 2026-11-16".
- **Track record**: 250 backtest days (t = 351…600). Each row has the forecast made before that day,
  the realised P&L and a breach flag (P&L < −VaR, unrounded).
- **Verdict**: the breach count against the nominal 2.5 and the finite-sample 3.5, the Kupiec test
  against the nominal 1% (LR, p-value, decision, direction), the Basel traffic-light zone, and a
  fixed note on why ~1.39% breaches is expected from this quantile rule.

The method is specified, with the expected numbers written down before any code, in
[`specs/001-portfolio-var-backtest/spec.md`](../specs/001-portfolio-var-backtest/spec.md) (M1–M7,
V1–V6). The interfaces are in [`contracts/`](../specs/001-portfolio-var-backtest/contracts/).

| Module | Role |
|---|---|
| `risk_service/core.py` | Pure calculation (M2–M7): `pnl_series`, `ewma_sigmas`, `residuals`, `interp_quantile`, `var_forecasts`, `backtest`, `kupiec`, `basel_zone`, `finite_sample_rate` |
| `risk_service/prices.py` | Loads the frozen CSV and refuses to start unless its SHA-256 is `9ea2eab1…0718ce3` |
| `risk_service/traderx_client.py` | Read-only GET calls to the TraderX account and position services (5 s timeout) |
| `risk_service/results.py` | Outcome precedence, provenance, and the `current` / `track_record` / `verdict` blocks |
| `risk_service/server.py` | `http.server` on port 18110: `/health`, `/api/v1/accounts`, `/api/v1/risk/accounts/{id}`, `POST /api/v1/risk/positions`, and the page at `/` |
| `risk_service/static/` | The page: banner, account picker, VaR, positions, verdict, track-record chart and table, basis |

Standard library only; no third-party packages at run time.

## Run

From the repository root (see [`quickstart.md`](../specs/001-portfolio-var-backtest/quickstart.md)):

```bash
# whole TraderX stack plus risk-service, every port published on 127.0.0.1 only
docker compose -f traderx/pricing-awareness-market-data/docker-compose.yml \
               -f deploy/tau.override.yml --project-name traderx-tau up -d --build
curl -s http://127.0.0.1:18110/health
open http://127.0.0.1:18110/        # pick "Test Account 20 (22214)"

# stop
docker compose -f traderx/pricing-awareness-market-data/docker-compose.yml \
               -f deploy/tau.override.yml --project-name traderx-tau down
```

Without Docker, against a TraderX whose account and position services are on 18088 and 18090:
`PYTHONPATH=risk-service python3 -m risk_service.server` (binds 127.0.0.1:18110).

## Test

```bash
PYTHONPATH=risk-service python3 -m pytest tests/unit tests/oracle -q            # tier 1, offline
RISK_BASE_URL=http://127.0.0.1:18110 TRADERX_BASE_URL=http://127.0.0.1:8080 \
  PYTHONPATH=risk-service python3 -m pytest tests/integration -q               # tier 2, stack running
```

The tests in `tests/` were written by a different AI model (gpt-5.6-terra via codex-cli) from the
spec and contracts only, committed before any implementation, and shown to fail first
(`validation/validator/red-run.txt`). The implementing model may not edit them. Disagreements are
recorded in [`disputes.md`](../specs/001-portfolio-var-backtest/disputes.md).

## Evidence

Every claim above points to a test and a saved run in
[`specs/001-portfolio-var-backtest/validation/runs/`](../specs/001-portfolio-var-backtest/validation/runs/):

| Claim | Test | Run |
|---|---|---|
| V1 hand example $33.3085, variant breach, forecast unchanged | `tests/unit/test_unit_calculation_contract.py::test_v1_hand_example_and_changed_day_variant` | `core-offline.txt` |
| V2 known-answer breach rate in [1.24%, 1.54%] | `…::test_v2_known_answer_coverage_uses_preregistered_seeded_series` | `core-offline.txt` |
| V4 no look-ahead, bit-identical | `…::test_v4_price_perturbations_cannot_change_forecasts_for_their_day` | `core-offline.txt` |
| V5 Kupiec and Basel table | `…::test_v5_kupiec_and_basel_reference_table` | `core-offline.txt` |
| V3 independent implementation agrees within $0.01, identical flags | `tests/oracle/test_oracle_independent_comparison.py`, `tests/integration/…::test_http_results_match_the_independent_oracle` | `core-offline.txt`, `integration.txt` |
| V6 outcomes and full provenance | `tests/integration/test_integration_risk_http.py::test_outcomes_precedence_and_provenance` | `integration.txt` |
| TraderX unchanged (SC-007) | `…::test_traderx_baseline_responses_are_preserved` | `integration.txt` |

## Sources and licence

New code in this folder is under the repository licence (Apache-2.0). The price history is
generated from seed 20261117 by
`specs/001-portfolio-var-backtest/data/generate_synthetic_prices.py` and anchored to the TraderX
snapshot closes (finos/traderX@d6e7fe4, Apache-2.0). No real market data is used.
