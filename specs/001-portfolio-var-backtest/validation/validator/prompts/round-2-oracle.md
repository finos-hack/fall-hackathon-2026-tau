# Round 2: independent implementation and comparison (tier 1, offline)

**Folder**: `tests/oracle/`. Write files only there.

**Scope**:

- **The independent implementation (spec V3).** Write a second implementation of spec M2–M7,
  from the spec alone. It must not import the module named in `contracts/calculation-api.md`.
- **The offline comparison (V3 and SC-004).** Compare the independent implementation with the
  module named in `contracts/calculation-api.md`. Use the frozen data file (located as described
  in `contracts/test-harness.md`) and the seeded accounts 22214 and 52355, with their positions
  given directly to both implementations as caller-supplied positions. Apply the agreement rules
  stated in V3 and SC-004.

**Not in this round**: comparisons over HTTP (round 3; round 3 receives the files in `tests/oracle/` and loads
the independent implementation from its file path), and the unit tests of round 1.

**Inputs**: the files listed in the system message, attached below.

**Output format**: as described in the system message.
