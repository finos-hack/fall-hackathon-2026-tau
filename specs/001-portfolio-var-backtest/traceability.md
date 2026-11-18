# Traceability — feature 001 (task T036)

One row per requirement and success criterion: where it is implemented, which validator-written
test checks it, and the saved run that shows the result. Test paths are abbreviated:
`U` = `tests/unit/test_unit_calculation_contract.py`,
`O` = `tests/oracle/test_oracle_independent_comparison.py`,
`I` = `tests/integration/test_integration_risk_http.py`.
Runs are in `validation/runs/`. Code paths are under `risk-service/risk_service/`.

Status: **verified** = a passing test in a saved run; **manual** = checked by hand at the gate and
recorded in `gate.txt`; **not yet verified** = no passing evidence yet (Principle IV).

`integration.txt` is the T033 run against the compose stack (6 passed). `integration-hostrun.txt` is
the same suite run earlier against a host-run service, kept as supporting evidence.

| ID | Code | Test | Evidence | Status |
|---|---|---|---|---|
| FR-001 one-day 99% VaR for an account | `core.py:var_forecasts`, `core.py:backtest`, `results.py:account_result` | U::test_v1_hand_example_and_changed_day_variant; O::test_published_history_agrees_with_independent_implementation; I::test_http_results_match_the_independent_oracle | core-offline.txt, integration.txt | verified |
| FR-002 positions, prices, market values, net value, two dates | `results.py:_current_block`, `prices.py:load` | I::test_caller_positions_match_account_22214_and_mark_provenance (blocks compared); I::test_http_results_match_the_independent_oracle (positions) | integration.txt (data_as_of, forecast_for, row dates asserted) | verified; price display also in the demo-22214.png |
| FR-003 current TraderX positions, read only; synthetic prices | `traderx_client.py:get_positions` (GET only), `prices.py` | I::test_http_results_match_the_independent_oracle (positions equal the seeded ones); I::test_traderx_baseline_responses_are_preserved | integration.txt | verified |
| FR-004 exactly 250 rows | `core.py:backtest`, `results.py:_track_record` | O::test_published_history_agrees_with_independent_implementation; I::test_http_results_match_the_independent_oracle | core-offline.txt, integration.txt | verified |
| FR-005 breach iff P&L < −VaR, unrounded | `core.py:backtest` | U::test_backtest_requires_strict_inequality_for_a_breach; U::test_v1_hand_example_and_changed_day_variant | core-offline.txt | verified |
| FR-006 verdict fields | `results.py:_verdict` | I::test_http_results_match_the_independent_oracle | integration.txt | verified |
| FR-007 Kupiec at nominal 1%; Basel thresholds | `core.py:kupiec`, `core.py:basel_zone` | U::test_v5_kupiec_and_basel_reference_table; U::test_finite_sample_rate_and_remaining_basel_boundary | core-offline.txt | verified |
| FR-008 account not found | `results.py:account_result` (step 3) | I::test_outcomes_precedence_and_provenance | integration.txt | verified |
| FR-009 no open positions | `results.py:risk_for_positions` (steps 4–5) | I::test_outcomes_precedence_and_provenance | integration.txt | verified |
| FR-010 missing price history, every security named | `results.py:risk_for_positions` (step 6) | I::test_outcomes_precedence_and_provenance | integration.txt | verified |
| FR-011 distinguishable outcomes, incl. zero volatility and positions unavailable | `results.py` (STATUS, precedence), `static/app.js:showOutcome` | I::test_outcomes_precedence_and_provenance; U::test_named_errors_are_raised_at_the_contract_conditions | integration.txt | verified for ACCOUNT_NOT_FOUND, NO_OPEN_POSITIONS, MISSING_PRICE_HISTORY, ZERO_VOLATILITY (subnormal caller quantity) and INVALID_REQUEST, with distinct codes and messages; `POSITIONS_UNAVAILABLE` over HTTP: **manual**, observed live in manual-positions-unavailable.txt (disputes D-007, D-011) |
| FR-012 no look-ahead | `core.py:ewma_sigmas`, `core.py:var_forecasts` | U::test_v4_price_perturbations_cannot_change_forecasts_for_their_day | core-offline.txt | verified |
| FR-013 determinism | `core.py` (pure functions) | U::test_indexing_current_forecast_and_determinism; I::test_repeated_requests_have_identical_numeric_result_blocks | core-offline.txt, integration.txt | verified; across a restart: **manual**, sc008-restart.txt |
| FR-014 frozen synthetic file, checksum enforced | `prices.py:load` (refuses a wrong SHA-256) | I::test_outcomes_precedence_and_provenance (data_sha256 in provenance) | integration.txt; `data/SHA256SUMS` | verified; refusal on a wrong file: **manual** |
| FR-015 provenance on every result | `results.py:provenance`, `results.py:_envelope` | I::test_outcomes_precedence_and_provenance; I::test_caller_positions_match_account_22214_and_mark_provenance; I::test_seeded_account_results_arrive_within_five_seconds | integration.txt | verified |
| FR-016 fixed verdict note | `results.py:VERDICT_NOTE` | I::test_http_results_match_the_independent_oracle (exact text) | integration.txt | verified |
| FR-017 page with picker; banner visible without scrolling | `static/index.html`, `static/app.js` | none (page not tested) | demo-22214.png | **manual** (banner at the top of the viewport; picker, VaR, dates, positions, verdict, chart, table, basis) |
| FR-018 TraderX unchanged | no file under `traderx/` edited; `deploy/tau.override.yml` only | I::test_traderx_baseline_responses_are_preserved; gate `git diff fbdfb38 --stat -- traderx/` | integration.txt, gate.txt | verified |
| FR-019 documented machine-readable results | `server.py`, contracts/http-api.md | every I test parses the JSON | integration.txt | verified |
| FR-020 caller-supplied positions | `results.py:caller_result`, `results.py:parse_caller_body` | I::test_caller_positions_match_account_22214_and_mark_provenance; I::test_outcomes_precedence_and_provenance | integration.txt | verified |
| SC-001 time to read a verdict | page | none | sc001-time.txt | **not yet verified** (Author, T035) |
| SC-002 under 5 s per seeded account | whole service | I::test_seeded_account_results_arrive_within_five_seconds | integration.txt, latency.txt | verified |
| SC-003 V1 to $0.0001; V2 band | `core.py` | U::test_v1_hand_example_and_changed_day_variant; U::test_v2_known_answer_coverage_uses_preregistered_seeded_series | core-offline.txt | verified |
| SC-004 two implementations agree within $0.01, 500 flags | `core.py` vs `tests/oracle/oracle_independent_var.py` | O::test_published_history_agrees_with_independent_implementation; I::test_http_results_match_the_independent_oracle | core-offline.txt, integration.txt | verified |
| SC-005 V4 perturbations | `core.py` | U::test_v4_price_perturbations_cannot_change_forecasts_for_their_day | core-offline.txt | verified |
| SC-006 provenance on all result types | `results.py:_envelope` | I::test_outcomes_precedence_and_provenance | integration.txt | verified except `POSITIONS_UNAVAILABLE` over HTTP: **manual**, manual-positions-unavailable.txt (provenance present) |
| SC-007 TraderX lookups unchanged | — | I::test_traderx_baseline_responses_are_preserved | red-run.txt (passes before), integration.txt | verified |
| SC-008 byte-identical across clean starts | `core.py` (pure) | I::test_repeated_requests_have_identical_numeric_result_blocks (same running service) | integration.txt, sc008-restart.txt | verified; across a risk-service restart: **manual**, byte-identical for 22214 and 52355 (sc008-restart.txt) |
