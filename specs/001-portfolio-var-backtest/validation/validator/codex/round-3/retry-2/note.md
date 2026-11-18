Round 3 review by the author (spec-conformance only), second and last retry. Rewrite tests/integration/
in full. The previous answer was correct apart from one point; keep everything else as it was.

1. Non-JSON TraderX bodies (contracts/test-harness.md § Baseline responses, "Format": "body": parsed
   JSON, "or a string when the body is not JSON"). One captured path answers with a plain-text body,
   not JSON, and its baseline entry stores that body as a string. The previous answer's request
   helper parsed every response body as JSON, so the SC-007 baseline test would raise a decode
   error on that path even when TraderX is unchanged. The "after" body must be read the same way the
   baseline was stored.
