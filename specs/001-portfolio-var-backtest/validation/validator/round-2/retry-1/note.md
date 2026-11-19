Round 2 review by the author (spec-conformance only). Rewrite tests/oracle/ in full, and write files
only under tests/oracle/. Every point below cites the clause your previous answer contradicted.
Re-read that clause; do not guess.

1. Undefined name (spec M4; contracts/calculation-api.md Params). The independent implementation
   passes a name `p` to its quantile function, but only `P` is defined, so every call raises
   NameError.

2. Pool size (spec M5). The pool for day t is the n residuals z_{t−n} … z_{t−1}, both ends
   included. The previous answer's pool stopped one residual short, so it held n − 1 values.

3. Current VaR and the last backtest day (spec M3 "Residuals", M5; contracts/calculation-api.md
   Functions table). Residuals exist for s = W+1 … N, and σ is needed up to s = N+1. The current
   VaR is the forecast for day N+1, using σ_{N+1} and z_{N−n+1} … z_N. The previous answer stopped
   one day early in both, so its current VaR was 0 and its backtest had 249 rows instead of 250.

4. Kupiec p-value (spec M6; contracts/calculation-api.md `kupiec`; common.md "standard library
   only"). The p-value is erfc(√(LR/2)), with nothing else applied. The previous answer imported a
   third-party package and changed that formula.

5. Imports (contracts/test-harness.md; tests/ has no __init__.py). The previous test files imported
   the oracle as a package (`tests.oracle...`), which fails with ModuleNotFoundError under pytest.
   Load the oracle module from its file path with importlib.

6. Account 52355 (spec, seeded accounts). Its positions are stated in spec.md. The previous answer
   used positions that appear nowhere in the inputs.

7. Agreement rules (spec V3 and SC-004). For both accounts: every current VaR and every backtest
   forecast within $0.01; breach flags identical on all 250 days; verdict fields identical, with LR
   and p-value within 1e-6. The previous comparison checked only the current VaR, and breach flags
   for one account.

8. Expected values come from spec.md or a contract (common.md "Rules for the tests"). A test named
   for V1 must use the V1 inputs and expected values. Tests that only check that a function runs, or
   that a dictionary has keys, do not verify anything the spec states.

9. End the answer with the "Open questions" section in plain text, even if it says "None".
