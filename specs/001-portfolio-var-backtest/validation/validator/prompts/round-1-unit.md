# Round 1: unit tests (tier 1, offline)

**Folder**: `tests/unit/`. Write files only there.

**Scope**: tests of the calculation contract (`contracts/calculation-api.md`), run against the
module it names. Cover:

- **spec V1**: the hand-checkable example, including its variant.
- **spec V2**: the known-answer coverage test.
- **spec V4**: the no-look-ahead perturbation test.
- **spec V5**: the Kupiec and Basel reference values, with the tolerance stated in V5.
- **SC-003 and SC-005**: as they apply to the calculation contract.
- **The contract's own behaviour**: the indexing convention, the "Guarantees the tests may rely
  on" section, the two error types and when each is raised, and the quantile edge case.

**Not in this round**: the independent second implementation (round 2), and anything that needs
the HTTP service or the running stack (round 3).

**Inputs**: the files listed in the system message, attached below.

**Output format**: as described in the system message.
