# TraderX Portfolio Risk (Hackathon Tau) Constitution

## Core Principles

### I. Spec-First, Feature-Scoped
Every change to code, configuration, or tests MUST trace to a numbered feature pack under
`specs/NNN-feature-name/` (`spec.md`, `plan.md`, `tasks.md`). Work not listed in the active
`tasks.md` MUST NOT be implemented. The human author writes and approves the spec; AI tools
MAY draft, review, and implement, but MUST NOT begin implementation before the author approves
`tasks.md`.

### II. Additive Delta on an Unmodified Base
The TraderX state 008 snapshot imported in commit `fbdfb38` (finos/traderX@d6e7fe4) is the
baseline. New behaviour MUST be delivered as new components (services, pages, tests). Edits to
baseline files are limited to wiring (compose, ingress, monitoring config), and each such edit
MUST be listed in the feature's `plan.md` with its reason. Existing 008 APIs and events MUST keep
their current contracts.
Rationale: `git diff fbdfb38` must show exactly what this project added.

### III. Deterministic, Offline Reproducible
Given the same inputs and seed, every computation MUST produce identical output. Any synthetic
data MUST be generated from a fixed, documented seed. The full stack and all tests MUST run on a
single workstation with no network access beyond pulling container images.

### IV. Evidence-Gated Completion
A requirement is complete only when a traceability table maps it FR → code location → test, and
that test passes. Claims in the README or demo MUST point to a test or a recorded output. A claim
without runnable evidence MUST be removed or labelled as not yet verified.

### V. Verifiable Without Trusting the Author
Risk numbers MUST be checked by at least three independent means:
(a) a hand-checkable example small enough to compute on paper;
(b) a known-answer test on synthetic data whose true distribution is known;
(c) an independent second implementation of the core calculation.
Expected values and tolerances MUST be written in the spec before the code runs, and MUST
account for finite-sample properties of the estimator (for example, the order-statistic
coverage of an empirical quantile), not only the nominal level. When a result misses its
expectation, the miss MUST be recorded with its cause; tolerances MUST NOT be widened after the
fact to make a test pass.

### VI. No Look-Ahead
A risk figure for date t MUST use only data observable before t. Each backtest MUST include a
test that perturbs data on or after t and shows the figure for t does not change.

## Project Constraints

- Deadline: submission by 2026-11-18 end of day ET; scope MUST fit the remaining time. One new
  service plus a static page; no rebuild of the Angular front end.
- Access: the stack binds to `127.0.0.1` only (local override file).
- Honest labelling: synthetic data, simplifications, and approximations MUST be labelled as such
  in the UI, API responses, and README.
- Data and licence hygiene: vendored or copied code MUST record its source, commit, and licence;
  no proprietary or licence-restricted data is committed.
- Every commit MUST carry a DCO `Signed-off-by` from the human author; AI tools MUST NOT run
  `git config`, set author identity, force-push, or rewrite pushed history.

## Development Workflow and Quality Gates

1. `/speckit-specify` → `/speckit-clarify`: no open `[NEEDS CLARIFICATION]` markers remain.
2. `/speckit-plan`: plan lists baseline files touched (Principle II) and the verification design
   (Principle V).
3. `/speckit-tasks` → `/speckit-analyze`: every FR maps to at least one task and one test.
4. Author approves `tasks.md`; only then `/speckit-implement`.
5. Gate before submission: all tests pass, the traceability table is complete, and the stack
   starts from a clean checkout with the documented command.

## Governance

This constitution overrides conflicting conventions in this repository. Only the human author
amends it. Each amendment updates the version line and records the change in the commit message.
Versioning: MAJOR for removing or redefining a principle, MINOR for adding a principle or
section, PATCH for wording. `/speckit-analyze` and review before each commit check compliance;
any deviation MUST be written down in `plan.md` with its reason.

**Version**: 1.0.0 | **Ratified**: 2026-11-17 | **Last Amended**: 2026-11-17
