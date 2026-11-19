Round 1 review by the author (spec-conformance only), second and last retry. Rewrite tests/unit/
in full. The previous answer fixed the numpy import, the error-condition tests and the test-calls-test
problem; keep those fixed. Four points remain. Each cites the clause the previous answer
contradicted. Re-read that clause; do not guess.

1. V1 variant (spec V1, "Variant"; contracts/calculation-api.md "Indexing convention"). The closes
   list holds C₀ … C₈, so C₈ is the element at index 8, the last one. The previous answer again
   changed the element at index 7 (C₇). That changes x₇ as well as x₈, so the forecast for day 8 is
   no longer the one the spec states. The spec also states that day 8 is not a breach in the main
   example and is a breach in the variant (BacktestRow.breach); the previous answer asserted
   neither.

2. V2 generator (spec V2 "Generator" and M3 "Seed", "Recursion", "Timing").
   - The V2 test reads the parameters object before the line that creates it, so it cannot run.
   - The M3 seed σ²_{W+1} is the mean of the squares of x₁ … x_W. The previous answer used the
     square of their sum divided by W.
   - σ_{W+1} is the seed itself and scales z_{W+1}. The recursion produces σ²_{s+1} from σ²ₛ and
     xₛ. The previous answer applied one extra update before generating x_{W+1}.

3. V4 (spec V4; contracts/calculation-api.md Guarantee 1; common.md "Do not weaken a
   pre-registered tolerance"). The criterion is bit-for-bit identical, that is exact equality of the
   two floats. The previous answer used a tolerance.

4. Output format (system message). End the answer with the "Open questions" section in plain text,
   even if it says "None". The previous two answers omitted it.
