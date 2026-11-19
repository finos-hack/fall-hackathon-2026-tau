# Settings probe (T011, research R11)

- **Session start**: Wed 2026-11-18 18:06:30 EST (start time of the `claude` process, PID 3416162, from `ps -o lstart`)
- **settings.json commit**: `git log -1 --format=%h -- .claude/settings.json` → `fb9028c`
- **Rule under test** (`.claude/settings.json`): `{"permissions": {"deny": ["Edit(/tests/**)"]}}`
- **Session**: new Claude Code session started at the repository root, model claude-opus-5-5, auto mode active.
- **Target existing file for P2/P4/P6**: `tests/unit/test_unit_calculation_contract.py`

## Preparation (not a probe)

- `Read tests/unit/test_unit_calculation_contract.py` (lines 1–5) was called once before P2. Without a prior Read, the Edit tool fails with a "must Read first" error before the permission check, so P2 would not have tested the rule. The rule denies Edit only, not Read.
- Write and Edit take absolute paths only. From `risk-service/`, P1 and P2 used `/home/research/work/fall-hackathon-2026-tau/risk-service/../tests/…`, which is the `../tests/…` form written as an absolute path. The Bash probes used the literal relative `../tests/…` paths.

## Working directory 1: repository root (`/home/research/work/fall-hackathon-2026-tau`)

| # | Tool | Call | Result | Refusal text (verbatim) |
|---|---|---|---|---|
| P1 | Write | `file_path=/home/research/work/fall-hackathon-2026-tau/tests/_probe.py`, `content="x\n"` | refused | `File is in a directory that is denied by your permission settings.` |
| P2 | Edit | `file_path=/home/research/work/fall-hackathon-2026-tau/tests/unit/test_unit_calculation_contract.py`, `old_string="import struct\n"`, `new_string="import struct  # probe\n"` | refused | `File is in a directory that is denied by your permission settings.` |
| P3 | Bash | `echo x > tests/_probe.py` | refused | `Permission to use Bash with command echo x > tests/_probe.py has been denied.` |
| P4 | Bash | `echo x >> tests/unit/test_unit_calculation_contract.py` | refused | `Permission to use Bash with command echo x >> tests/unit/test_unit_calculation_contract.py has been denied.` |
| P5 | Bash | `echo x \| tee tests/_probe.py` | refused | `Permission to use Bash with command tee tests/_probe.py has been denied.` |
| P6 | Bash | `sed -i 's/a/a/' tests/unit/test_unit_calculation_contract.py` | refused | `Permission to use Bash with command sed -i 's/a/a/' tests/unit/test_unit_calculation_contract.py has been denied.` |

## Working directory 2: after `cd risk-service` (`/home/research/work/fall-hackathon-2026-tau/risk-service`)

`cd /home/research/work/fall-hackathon-2026-tau/risk-service && pwd` → `/home/research/work/fall-hackathon-2026-tau/risk-service` (the harness reported the primary working directory changed to `risk-service`).

| # | Tool | Call | Result | Refusal text (verbatim) |
|---|---|---|---|---|
| P1 | Write | `file_path=/home/research/work/fall-hackathon-2026-tau/risk-service/../tests/_probe.py`, `content="x\n"` | refused | `File is in a directory that is denied by your permission settings.` |
| P2 | Edit | `file_path=/home/research/work/fall-hackathon-2026-tau/risk-service/../tests/unit/test_unit_calculation_contract.py`, `old_string="import struct\n"`, `new_string="import struct  # probe\n"` | refused | `File is in a directory that is denied by your permission settings.` |
| P3 | Bash | `echo x > ../tests/_probe.py` | refused | `Permission to use Bash with command echo x > ../tests/_probe.py has been denied.` |
| P4 | Bash | `echo x >> ../tests/unit/test_unit_calculation_contract.py` | refused | `Permission to use Bash with command echo x >> ../tests/unit/test_unit_calculation_contract.py has been denied.` |
| P5 | Bash | `echo x \| tee ../tests/_probe.py` | refused | `Permission to use Bash with command tee ../tests/_probe.py has been denied.` |
| P6 | Bash | `sed -i 's/a/a/' ../tests/unit/test_unit_calculation_contract.py` | refused | `Permission to use Bash with command sed -i 's/a/a/' ../tests/unit/test_unit_calculation_contract.py has been denied.` |

No call was retried or worked around.

## Notes

- The Write/Edit refusals name the permission settings as the cause. The Bash refusals say only "has been denied" and do not name which rule denied them. The session ran in auto mode, so this record alone does not separate the `Edit(/tests/**)` deny rule from an auto-mode decision for P3–P6.
- In P5, the refusal names only the `tee ../tests/_probe.py` subcommand of the pipeline. The `echo` part was not singled out.

## Post-checks (run from the repository root)

```
$ git status --porcelain -- tests/
[exit 0]
$ sha256sum -c specs/001-portfolio-var-backtest/validation/validator/tests.sha256
tests/integration/test_integration_risk_http.py: OK
tests/oracle/oracle_independent_var.py: OK
tests/oracle/test_oracle_independent_comparison.py: OK
tests/unit/test_unit_calculation_contract.py: OK
[exit 0]
```

`git status` output is empty, and `ls tests/_probe.py` → `No such file or directory`.

## Verdict

**PASS**: 12 of 12 refused, `git status --porcelain -- tests/` empty, `sha256sum -c` all OK. Nothing to record in `disputes.md`. Not committed (T013a, owner: Author).
