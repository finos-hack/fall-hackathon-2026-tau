Round 2 review by the author (spec-conformance only), second and last retry. Rewrite tests/oracle/
in full, and write files only under tests/oracle/. The previous answer fixed the 52355 positions, the
undefined name and the third-party Kupiec formula; keep those fixed. These points remain, most
important first. Re-read each cited clause; do not guess.

1. The offline comparison is missing (round 2 instructions, "Scope"; spec V3 and SC-004). The
   previous test file never calls the module named in contracts/calculation-api.md, so nothing is
   compared. Round 2 has two parts: the independent implementation, and a comparison of it with
   that module for accounts 22214 and 52355 under the V3 agreement rules.

2. The independent implementation returns no forecasts at all (spec M5). Its pool loop collects
   z_{t−n} … z_{t−2}, which is n − 1 values, and then skips every day because the pool has fewer
   than n values. The pool is z_{t−n} … z_{t−1}: n values, both ends included. The V1 example gives
   an empty result instead of $33.3085.

3. Day N+1 is still missing (spec M3, M5; contracts/calculation-api.md Functions table). σ is needed
   for s = W+1 … N+1, and var_forecasts covers t = W+n+1 … N+1. The previous answer stops at N, so
   the current VaR is 0.

4. kupiec raises UnboundLocalError for 0 breaches: an import statement inside the function makes
   that module's name local to the whole function.

5. Loading the oracle (contracts/test-harness.md; round 2 instructions). After loading the module
   from its file path with importlib, use the module object it returns. The previous answer then
   imported it again by name, which fails with ModuleNotFoundError.

6. Scope and rules (common.md "Rules for the tests"). V2 belongs to round 1; do not write it here.
   Standard library only: the previous answer imported numpy. Every expected value must come from
   spec.md or a contract: for example, the contract's var_forecasts covers t = W+n+1 … N+1, which is
   not 601 keys.

7. End the answer with the "Open questions" section in plain text, even if it says "None".
