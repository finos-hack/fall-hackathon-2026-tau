# Round 3: integration tests (tier 2, the running stack)

**Folder**: `tests/integration/`. Write files only there.

**Scope**: tests of the HTTP contract (`contracts/http-api.md`) against the running service.
Base URLs come from the environment variables in `contracts/test-harness.md`. Cover:

- **spec V6**: the outcome cases.
- **FR-011 and the outcome precedence**: every outcome and its HTTP status, and the precedence
  order in `contracts/http-api.md`.
- **FR-020**: caller-supplied positions against the account path for the same positions.
- **SC-006 and FR-015**: provenance on every response type, error outcomes included.
- **SC-007**: the baseline comparison against the file named in `contracts/test-harness.md`
  § Baseline responses, with the comparison rules in SC-007.
- **SC-008**: the determinism comparison as stated in SC-008.
- **V3 and SC-004 over HTTP**: compare the service's results with the independent implementation
  in `tests/oracle/`. Its files are attached as input 9. `tests/` has no `__init__.py`, so load the
  oracle module from its file path with `importlib`; do not use a package import.
- **SC-002**: the response-time criterion.

**Not in this round**: the calculation-contract unit tests (round 1), and writing or changing
anything in `tests/oracle/` (round 2).

**Inputs**: the files listed in the system message, attached below.

**Output format**: as described in the system message.
