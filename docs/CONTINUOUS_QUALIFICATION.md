# Continuous qualification

The Windows workflow tests existing capabilities without requiring Codex, an AI
provider, owner evidence or a repository write token. It is a development gate,
not a release publisher. Source remains 0.2.0.dev1 until clean-machine, human,
license and release-authorization gates justify an RC. Python's compatible future
spelling is 0.2.0rc1; do not infer that the current artifacts carry this version.

## GitHub Actions

[Windows qualification](../.github/workflows/windows-qualification.yml) uses JSON
syntax, a YAML subset, so the standard-library tests can inspect the exact parsed
workflow without adding a YAML dependency. Actions are pinned to full commit SHAs
resolved from official releases: checkout v7.0.1, setup-python v7.0.0 and
upload-artifact v7.0.2. Updates require review and tests.

The source matrix selects Python 3.12 and 3.14 x64 on the documented
[windows-2025 runner](https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md).
This is Windows Server, not a clean Windows 11 consumer account. If the requested
Python or pinned package version is unavailable, setup fails visibly; no fallback
version is silently substituted. Each job creates a project-local venv.

Standard unittest runs include unit/integration, capsule, journal, GUI widgets,
recovery, archive safety, manifest and workflow-boundary checks. The package job
depends on matrix success, builds the wheel and both executables, exercises the
portable verifier, installs the wheel and creates a component inventory.
CI is authored and locally inspected; only an actual GitHub run can establish its
hosted result. Logs must identify the commit, Python version and runner image.

Pull requests targeting main or a branch in the existing stack trigger checks.
A push to the qualification branch provides a route before an initial PR exists.
Concurrency groups cancel superseded runs for the same branch to limit duplicate
work. Manual dispatch is declared but requires the workflow on the default branch
according to [GitHub's dispatch rules](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).
Do not merge merely to unlock dispatch. PRs #1–#4 do not retroactively acquire this
new workflow; their code is exercised as ancestry of D. Eventual reviewed merge
order is #1, #2, #3, #4, then D, checking and retargeting dependent bases only with
owner authorization. No existing PR is modified by this work.

Permissions are contents:read; checkout does not persist credentials. No
implicit PR merge revision is substituted: checkout selects the PR head SHA or
the push SHA, and the test summary records HEAD, Python and platform. No
pull_request_target, repository writes, secrets, provider access, automatic release,
merge or binary upload exists. Jobs have 20/25-minute timeouts. Only seven fixed
synthetic diagnostic filenames may be copied for upload, each capped at 2 MiB;
oversized diagnostics are explicitly omitted. Retention is seven days. No database,
capsule, environment, executable or ZIP is uploaded. Package-manager network access
is for explicit pinned dependencies and is not application telemetry.

## Fixture architecture and failure evidence

The unmodified Checkpoint C baseline reproduced 151 compatibility passes and
151 standard tests with four failures / 102 error entries under the restricted
worker. Historical outputs are retained. A new synthetic-only directory helper
replaces TemporaryDirectory in affected test fixtures. It inherits permissions
inside the project, never changes existing ACLs, never patches production modules,
and refuses cleanup outside its owned directory. Do not store secrets or real
investigation evidence in these fixtures.

Git's read-only object files exposed four cleanup errors during development.
Cleanup now clears only the DOS read-only flag on files owned by that disposable
fixture. Other permission errors propagate. No ACL repair, global chmod policy or
account permission change is used. The original compatibility runner is preserved
and executed separately, even when the standard command succeeds.

The demo integration test now waits for observed synthetic events instead of a
fixed 0.9-second delay. Existing event-loop/observer polling sleeps are bounded
poll intervals, not assumptions that startup completed. The deliberately sleeping
specimen and timeout canary remain bounded owned test processes. No test observer
is allowed to terminate an attached specimen.

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe scripts/run_sandbox_checks.py
.venv/Scripts/python.exe scripts/ci_checks.py --destination cache/repeated-check-NEW --repeat 2
```

The measurement wrapper invokes the standard command without monkeypatching. It
records exits, timeouts, elapsed times and sampled RSS for the launched process
and up to 64 descendants. RSS sums can double-count shared pages; 100ms samples
are not exact peaks. Record failures and do not describe a changing source tree
as a repeated identical-input experiment. Final repeated runs must use fixed code.

## Recovery and runtime boundaries

Existing idempotency, stale-revision, corruption, interrupted-transaction and
backup mechanisms are retained. Added tests restore a synthetic journal backup,
resolve citations against unchanged capsules, read a backup with SQLite mode=ro,
reject a corrupted copy and preserve source hashes.

Report export first writes and fsyncs a unique .partial file. Only then is the
requested final filename published without overwriting an existing file. A failed
write/flush leaves the partial available for explicit inspection. It is not a
completed report and is never imported or executed automatically. POSIX publication
uses an exclusive hard link; unsupported filesystems can report failure. Windows
uses non-overwriting rename. Crash/power-loss durability beyond the tested SQLite
and fsync boundaries is not guaranteed.

Unicode/space-containing case paths, denied GUI operations and case reopening are
tested. Arbitrarily long paths remain subject to Windows/filesystem limits; no
global long-path policy is changed. No optional provider configuration is loaded
on startup. Missing Git does not disable offline case review.

## Build and dependency evidence

The existing local hash lock remains mandatory by default. CI uses an explicitly
selected newly recorded runner lock because hosted Python installations differ
from the workstation. That records observed inputs and checks drift during the
build; it is not pre-authenticated upstream provenance. The actual lock digest is
included in the artifact manifest. Exact dependency versions are pinned, but
authenticated, hash-pinned upstream download reconstruction remains incomplete.

`scripts/component_inventory.py` emits an **APM local component inventory**, not a
claimed CycloneDX-compliant SBOM. It records package versions, declared requirements,
runtime/build relationships, licenses where declared, relative binary filenames,
SHA-256 values and unknown versions/redistribution rights. No absolute machine
paths are included. Complete binary-to-upstream-license mapping, Microsoft runtime
redistribution terms, upstream authenticity and supported OS coverage remain open.
No new runtime dependency or WiX acceptance is introduced.

`scripts/release_gates.py` validates a complete gate inventory. PASS requires
evidence references; pending, blocked, failed or not-applicable gates cannot be
mistaken for universal release readiness. The validator checks declarations, not
the truth of evidence. Gate reports are generated locally and excluded from Git.

## Three-way source qualification

The original two 163-test logs are preserved as an earlier Mission 006 snapshot.
Mission 006.5 adds a distinct owner/CI gate regression and an owner-shell script.
Fresh results must identify the final source manifest and committed revision;
earlier logs must not be relabeled as tests of later code.

`scripts/owner-verify-windows.ps1` is for ordinary owner PowerShell outside the
engineering worker. Supply the reviewed commit, complete source manifest, its
separate SHA-256 and the approved Python executable. It verifies tracked file
inventory and hashes before testing, runs ordinary unittest, rechecks hashes,
and creates a unique local report containing versions, counts, duration and exit.
The operator's shell declaration is recorded, not cryptographically authenticated.
The publication handoff supplies exact parameter values after committing.
Do not execute it inside Codex and call that owner verification.

Release-gate schema 2 separates standard local tests, owner Windows tests and
GitHub CI; schema 1 remains readable. Neither pending external layer can be
substituted with compatibility results. Only all three passing at the same
committed source (or an independently justified difference) supports a three-way
verification statement. Clean-machine and human visual acceptance are additional
gates, not consequences of three automated test passes.


## Tk lifecycle regression gate

Both source jobs also run `scripts/check_tk_lifecycle.py` in fresh processes with
reversed adjacent test ordering. Bounded lifecycle logs are included in the
existing diagnostic allowlist. Standard and focused runners reject known Tcl/Tk
shutdown diagnostics even if the process returns zero. See
[Tk ownership repair](TKINTER_THREAD_OWNERSHIP.md) for reproduction and limitations.
