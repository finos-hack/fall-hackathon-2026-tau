Round 3 review by the author (spec-conformance only). Rewrite tests/integration/ in full. The previous
answer was close; keep everything that is not named below. Two points, each citing a clause.

1. positions_read_at on the TraderX account path (contracts/data-model.md Provenance). For a result
   whose positions were read from TraderX the field is a UTC ISO-8601 timestamp string. The previous
   answer's provenance helper compared the field with `is True` for those results, so every correct
   OK response on the account path would fail that assertion.

2. positions_read_at for the other account-path outcomes (contracts/data-model.md Provenance, as
   clarified on 2026-11-18). Re-read the clarified row. In particular, the account with no open
   positions (44044) is a case where the TraderX position lookup was read.
