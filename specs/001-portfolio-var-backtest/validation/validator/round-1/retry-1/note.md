Round 1 review by the author (spec-conformance only). Rewrite tests/unit/ in full. Every point
below cites the clause your previous answer contradicted. Re-read that clause; do not guess.

1. Standard library only (common.md "Rules for the tests"; contracts/calculation-api.md "Python").
   The previous answer imported numpy. Use the standard library `random` module for all draws.

2. V1 variant (spec V1, "Variant"). The variant changes C₈, the close on day 8 (the last of
   C₀ … C₈). The previous answer changed C₇ instead, so x₇ and x₈ both changed and the stated
   expectations no longer applied.

3. V2 generator (spec V2 "Generator" and M3). The true volatility must follow M3 exactly,
   including the M3 seed for σ²_{W+1}. The previous answer seeded the recursion differently, so
   its residuals are not i.i.d. by construction. Also remove random generators that are created
   but never used.

4. V4 (spec V4; contracts/calculation-api.md Guarantee 1). The quantity compared is the forecast
   VaRₜ for the perturbed day t itself, and the comparison is bit-for-bit (exact equality), not a
   tolerance. The previous answer compared the forecast for day N+1, which legitimately depends on
   the perturbed data.

5. Quantile edge (spec M4; contract Guarantee 4). The rule "when k+2 > n" uses n = the number of
   values passed to interp_quantile. The previous edge-case test used a pool where k+2 ≤ n, so its
   expected value contradicts M4.

6. Error conditions (contract Functions table, "Series length sets everything").
   var_forecasts and backtest raise InsufficientHistoryError when N < W + n. Several previous tests
   called them with N < W + n and expected no error. A P&L series whose warm-up values are all zero
   raises ZeroVolatilityError (contract Types; M3 seed); one previous test expected no error and an
   empty result for that case.

7. Do not call test functions from other test functions. pytest runs each test once; calling them
   again only repeats the slow V2 run.

8. End the answer with the "Open questions" section, as the system message requires, even if it
   says "None".
