# Living Observatory engineering checkpoint

## Missions 006 / 006.5: continuous and three-way qualification, 2026-10-11

Read-only GitHub checks now confirm PRs #1–#4 remain open and unmerged with
the expected stacked heads through Checkpoint C. This supersedes the historical
remote-publication status in the Mission 005 entry below. Development continues
in an isolated checkout based on C; the original main worktree is preserved.

Implemented a Windows 3.12/3.14 CI matrix, exact-head checkout, pinned Actions,
bounded synthetic diagnostics, package qualification and component inventory.
Repository permissions are read-only. CI does not install Codex or use owner
evidence, provider credentials, paid APIs or release publication. Hosted execution
is still pending; an authored workflow is not a successful run.

The unchanged C baseline produced 151 compatibility passes and standard results
of four failures / 102 error entries. A separate no-APM probe reproduces access
denial in private temporary directories under the restricted token. Synthetic
fixtures now inherit project permissions without changing ACLs or production
storage policy. Git read-only object cleanup is scoped to owned fixtures.
The demo test waits for actual events and always stops its own controller.

The retained first final runs passed 163 tests in 92.238s and 95.142s.
Subsequent three-way gate work increased the suite to 164: two development
standard runs passed in 90.853s and 89.537s, and compatibility passed in 90.714s.
These are distinct snapshots. Exact committed-source validation and hashes belong
in the final local handoff; do not reattribute earlier logs to later revisions.
Owner PowerShell execution and GitHub Windows execution remain PENDING.

Report export now flushes a unique partial before publishing a new final filename.
Focused recovery tests cover interruption, backup restoration, read-only inspection,
citations, corruption rejection and unchanged source evidence. Existing capsule
and journal serialization remains unchanged.

Two fresh local builds have equal portable ZIP and wheel hashes, with all 150
bundled file inventories equal. Both packaged executables passed synthetic native
widget workflows and fresh-process reopening; the wheel passed isolated offline
installation and workflow checks using the declared restricted-build accommodation.
This is same-machine evidence, not clean Windows or human visual acceptance.
The component inventory lists nine build/runtime packages and 76 binaries, with
unresolved binary license mappings and upstream authenticity. It is not a claimed
CycloneDX SBOM. No new dependency or global installation was introduced.

The owner test script verifies a complete reviewed source manifest and exact
commit, records ordinary unittest results separately, and never relabels worker
results as owner results. Release gates preserve all three verification layers.
Version remains 0.2.0.dev1; clean-machine, human, license and release-authorization
gates remain pending. See [qualification architecture](CONTINUOUS_QUALIFICATION.md)
and [clean Windows acceptance](CLEAN_WINDOWS_ACCEPTANCE.md).

Next action: execute the reviewed Checkpoint D owner publication handoff, then
inspect its first Windows CI run at that exact head. Ordinary owner tests use the
separate manifest-bound script. Neither task authorizes merging or a binary release.

## Mission 005: independent qualification, 2026-10-11

The immutable cognitive and desktop checkpoints were reconstructed and their
complete trees and bundles checked against retained manifests. GitHub still has
only main and the Living Observatory checkpoint. Read-only GitHub commit lookup
found neither subsequent commit. Shell Git cannot reach the configured proxy;
the connector's prior mandatory-approval denial remains unresolved. No publication,
merge, release or protected-engine change is claimed.

Implemented a standalone bounded portable verifier, explicit GUI operation
outcomes (including worker completion during shutdown), a twelve-component
capability inventory with closed-schema/local-reference validation, build input
hash locks and deterministic ZIP serialization. Corrected outdated workflow
labels and installed-data-path documentation. Existing reports already provide
readable summaries, escaped content and correction history; their evidence format
was preserved. No automatic recent-case scan or external provider was introduced.

Baseline: 135 compatibility passes; standard 135 tests, three failures and 102
error entries. Final source: 151 compatibility passes; standard 151 tests, four
failures and 102 error entries. Independent no-APM permission and Git probes
reproduce inaccessible private temporary directories under a restricted token;
inherited-permission fixtures succeed. New explicit outcomes expose fixture
PermissionError earlier. Owner-shell testing is PENDING OWNER EXECUTION.

The original portable ZIP and newly built portable application both pass the
external same-machine verifier. Both executables complete synthetic native-widget
workflows and a fresh OS process verifies each retained four-revision journal.
Two identical-input build directories produced identical ZIP and wheel bytes.
A final documentation-refreshed build was separately qualified; the final wheel
was installed and exercised in a disposable isolated environment. No clean-machine,
ordinary-user, human-visual, installer or public-release acceptance is claimed.

The retained owner database still has 108 integrity-verified records and 21
resolved citations. Database/WAL and protected engine hashes match the baseline.
No genuine Codex workload was repeated. Source evidence remains separate from
interpretations, and no execution authority was introduced.

See [qualification](INDEPENDENT_QUALIFICATION.md),
[distribution gates](DISTRIBUTION.md), and the
[capability contract](../capabilities/apm-capabilities-v1.json).
Detailed paths, hashes, full logs and publication scripts are retained locally in
ignored mission reports, not published source. Next: run the audited final portable
candidate in a clean ordinary-user Windows VM without Python/Codex, capture the
visible demonstration/reopen/report checklist and preserve results.


## Latest: unattended desktop engineering checkpoint, 2026-10-10

Checkpoint A is preserved locally at `1f43147758c4ba88ac4af8b32ce42f49b25e3995`
on `feature/apm-cognitive-holmes-v1`, based on PR #1 head `ab019da`. Its 118-file
reviewed tree contains 44 changes and passes 130 compatibility tests. GitHub
publication was blocked by mandatory tool approval under policy `never`; no new
remote branch/PR was created. The verified bundle, full manifest, staged diff and
ready-to-run stacked publication handoff are retained locally. PR #1 is unchanged.

The subsequent desktop implementation adds a useful welcome state, synthetic
onboarding, guided native investigation pages, keyboard navigation, per-user data
defaults and readable evidence-cited reports. Current capsule and journal formats,
Genesis observation, replay and qualification review remain compatible. Completed
worker callbacks are released and close waits for an active operation.

Final compatibility suite: **135 passed in 88.315 s**. Final standard suite:
**135 run in 79.271 s, 3 failures and 102 error entries**. The new desktop fixture
postconditions/cleanup also encounter the known restricted temporary-directory
problem; the standalone no-APM diagnostic reproduces it. Owner PowerShell is
**PENDING OWNER EXECUTION**, not assumed successful. Historical failing/intermediate
logs remain preserved, including a separate Tk retention issue fixed before the
passing compatibility run. No global ACL or Python configuration was changed.

The retained owner qualification still has 108 verified records and 21 resolved
citations, with unchanged DB/WAL and protected executable hash. No Codex workload
was repeated. Source and both packaged executables passed fresh-process synthetic
Holmes workflows; the parent independently recomputed packaged journal chains.
The wheel installed in a disposable environment and passed the same workflow.
Build/install used an explicit, local restricted-temp accommodation after the
unmodified wheel backend failed. Portable executables and wheel remain private
development artifacts with hashes and inventories, not published downloads.

Visible human acceptance, clean Windows installation, full transitive binary
redistribution clearance, signing, installer upgrade/uninstall and lifecycle data
retention remain UNVERIFIED. WiX 7 installer work is blocked pending owner EULA/
maintenance applicability decision. Checkpoint B is a local source preservation
handoff stacked on A; the same publication approval block remains in force.
See [checkpoint details](DESKTOP_CHECKPOINTS.md), [desktop guide](DESKTOP_GUIDE.md),
[distribution gates](DISTRIBUTION.md) and [ADR 0003](decisions/0003-desktop-distribution.md).

The precise next task is clean ordinary-user Windows x64 qualification of the
portable build, without Python, using the visible demonstration and retained-case
checklist. The historical development results follow without replacing old evidence.

## Earlier engineering milestones

This development checkpoint extends Genesis at commit
`717aaa50c592d92e7369711567374c5c801f7f2b`. It preserves the Python/Tk architecture,
existing JSONL recordings and passive observers. psutil remains the only runtime
dependency. This page is a reviewed aggregate summary, not a recording export.
Raw reports, database files, session/event identifiers, machine inventory and
private observation details remain local and excluded from publication.

## Implemented scope

| Capability | Implementation and limits |
|---|---|
| Observe | Existing scoped process/workspace observers plus explicitly piped public Codex exec JSONL. Strict allowlisting excludes reasoning, messages, output and private histories. Reports and independent host observations remain distinct |
| Remember | SQLite WAL memory alongside preserved Genesis JSONL; stable event IDs, stream sequences, bounded transactions, read-only queries, backup and a SHA-256 receipt chain. SQL and JSONL are not one atomic transaction |
| Investigate | Deterministic last-100-record review with evidence citations and a saved checkpoint. Findings expose omitted history and unknown causes; no provider-generated explanation |
| Cooperation foundations | Session-scoped reporter/reader capabilities, authenticated loopback receiver, durable retry outbox, native Memory / Ask and human opinions. No instruction submission, command execution API or bidirectional dialogue bridge |

Architecture alternatives, protocol, bounds and trust limitations are in
[OBSERVATORY.md](OBSERVATORY.md). See [security](../SECURITY.md),
[capability qualification](WORKSTATION_CAPABILITIES.md), and
[the AEGIS comparison](research/AEGIS-COMPARATIVE-ANALYSIS.md) with its
[attribution register](research/AEGIS-ATTRIBUTION-REGISTER.md). AEGIS was inspected
at a pinned commit; no code/assets were reused or AEGIS benchmarks executed.

## Owner-run protected Codex qualification

The owner executed the authorized disposable engineering fixture using the protected
Codex CLI `0.156.0-alpha.17`. For publication, the retained local database was reopened
read-only, every session page was inspected programmatically, counts were recomputed
independently of the harness summary, and chain/index/counter integrity was checked
against the recorded final tip. The source database's bytes remained unchanged.

| Evidence | Checked result | Basis |
|---|---:|---|
| Public Codex reports | 5 | Stored reporter-origin, AGENT_REPORTED Codex records |
| Completed command failure | 1 evidence ID | Stored completed command report for the authorized test, with nonzero integer exit code |
| Codex turn completed | Yes | Stored public lifecycle report |
| Host process-generation observations | 81 records | Stored host-origin, OBSERVED process records with birth time |
| Child-generation observations | 68 records | Same host subset with child PID differing from root PID |
| Final SQLite history | 108 verified records | Read-only integrity check and complete paginated count |
| Saved investigations | 2, both cite the command failure | Evidence references resolved within retained history; reopened investigation also cites it |
| Companion recovery | 0 pending, 0 loss count | Read-only reopening of the durable outbox |
| Receiver delivery | 5 accepted requests, companion exit 0 | Retained harness result; request count is not a general event count |
| Earlier restart verification | 106 records, successful | Retained harness result, before two investigations were saved |
| Harness timeout/errors | No timeout; zero reported errors | Retained harness result, not a new live execution |
| Native GUI | Evidence/details/Ask and a cited failure passed | Retained automated native Tk widget result; first page contains 100 records |
| Protected executable | Reported unchanged; current hash matches recorded pre-run hash | Read-only binary hash check; no engine launch, repair or installation change during publication |

These are real observations of a deliberately failing fixture, not evidence that
an unrelated production task succeeded. Record counts are not unique process counts.
The owner describes the run as authenticated; **account identity is not independently
verified**, and the harness deliberately retains `authenticated_workflow=UNVERIFIED`.
Local capability authentication does not cryptographically attest a producer's
identity or truth. PID ancestry and receipt timing do not prove command-to-process
causation. An unkeyed hash chain is not a source-authenticity or completeness proof.
Visible/manual GUI inspection is not established by withdrawn-widget checks.

Earlier restricted-identity attempts failed before any public event, with fixed
access-denial/runtime-initialization diagnostic labels. Those failures remain valid
historical evidence; they are not an authentication diagnosis and are not erased
by the later owner-run success. A previous controlled native workload and isolated
CLI failure probe remain separately labelled and locally retained.

## Verification on 10 October 2026

| Run | Actual result |
|---|---|
| Historical Genesis compatibility baseline | Original 66 tests passed |
| Earlier Observatory compatibility checkpoint | 89 passed, 0 failures/errors/skips, 36.379 s |
| Earlier required standard invocation | 89 tests, 1 failure, 97 error entries, 19.511 s |
| Publication compatibility invocation | 89 passed, 0 failures/errors/skips, 41.048 s |
| Publication required standard invocation | 89 tests, 1 failure, 97 error entries, 21.039 s |

The suites exercise redaction, scope/role rejection, unknown schemas, malformed
frames, durable retry/deduplication, atomic rollback, crash recovery, backup,
integrity checks, passive replay, specimen-preserving Stop and native GUI integration.
The new qualification tests reject lifecycle-only, synthetic and unrelated-command
evidence as substitutes for the selected workload. Passing fixture tests do not
establish production coverage or an adversarial security certification.

A standalone diagnostic without APM imports reproduced the Windows temporary-directory
failure. Under the restricted process token, `os.mkdir(0700)` and `tempfile.mkdtemp()`
create directories but child writes/scanning/removal fail; inherited-access
`os.mkdir(0777)` works. This agrees with
[Python's Windows directory-mode behavior](https://docs.python.org/3.14/library/os.html#os.mkdir).
The standard-suite controller failure is a consequence of that inaccessible fixture.
No ACL, privilege, global Python setting or installed component was changed. The
compatibility runner changes directory creation only inside its test process and
repository scope; its pass is explicitly not a standard-command pass. No causal
equivalence between this failure and Codex startup trouble is claimed.

Earlier synthetic storage samples retained locally measured 1,000 records at
38.79 records/s with individual durable commits and 632.65 records/s with atomic
batches of 32, both WAL/synchronous FULL. They are single storage samples, not
agent-overhead, transport-throughput or UI-latency guarantees; publication did not
rerun those completed benchmarks.

## Reproduce within authorized scope

Use the repository's isolated environment. The first two commands run local tests;
the diagnostic creates only new ignored fixtures. The last command launches the
protected engine and requires an explicitly authorized disposable workload and a
working owner runtime context. Do not substitute another CLI or weaken security to
make it pass.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\run_sandbox_checks.py
.\.venv\Scripts\python.exe scripts\diagnose_tempdirs.py
.\.venv\Scripts\python.exe scripts\qualify_codex.py --seconds 45
```

Harnesses create new ignored directories. Preserve the original local artifacts;
do not force-add databases, credentials, histories, screenshots or raw reports to
Git. Public verification is limited to this reviewed aggregate summary.

## Remaining engineering work

The working slice is Observation → Persistent Memory → Investigation → Human-AI
Cooperation Foundations. It is not the complete Living Observatory or completed
bidirectional human-AI communication. Pending capabilities include authenticated
app-server integration, explicit agent/thread-to-host binding, causal evidence
relationships, indexed failure comparisons, provider consent UI, MCP, stronger
OS capability-file isolation, Windows 11 qualification, timed SQL replay, extended
overload testing and installer delivery.

## Native qualification review follow-up — 2026-10-10

The next implementation is complete locally: a separate read-only native window
opens an explicitly selected database, verifies a bounded consistent snapshot,
pages the complete selected session, summarizes all its records and resolves saved
investigation citations across pages. It presents whole-database and session chain
tips, saved checkpoint matches/mismatches, evidence classes and unknowns. The
original Memory / Ask window, last-100 investigation algorithm, Genesis observers,
receiver and replay behavior are preserved. See [review design](OBSERVATORY.md#read-only-qualification-review).

Remote inspection confirmed PR #1 remains open with four commits, head
`ab019da0d2c970efab80fe4878b7f2ec55cb9370`, targeting unchanged `main` at
`717aaa50c592d92e7369711567374c5c801f7f2b`. The primary workspace still has the
previous uncommitted checkpoint; new changes are additive local work. No commit,
push, merge, release or repository-setting change was made in this follow-up.

| Verification | Current result |
|---|---|
| Required standard unittest command | 98 tests in 36.774 s; 1 failure, 97 error entries; restricted-token temporary-directory failures remain |
| Documented compatibility runner | 98 tests passed in 54.567 s; zero failures/errors/skips |
| New sanitized review tests | Nine tests cover full pagination, consistent snapshots during fixture writes, read-only enforcement, citations and scope isolation, missing evidence/checkpoint mismatch, contradictory reports, item reuse across turns, tampering/expected-tip failure, empty/missing databases, bounds, cancellation and native widgets |
| Retained owner session through new reviewer | 108 records, pages 100 + 8; 5 Codex reports, one reported failed command, one completed-turn report; 81 host process-generation records including 68 child records |
| Retained evidence classes | 91 OBSERVED, 5 AGENT_REPORTED, 2 INFERRED, 8 UNKNOWN, 2 UNAVAILABLE |
| Saved investigations and integrity | Two saved investigations; all 21 references resolved; no missing references or checkpoint mismatches; whole snapshot verified against the separately retained final tip |
| Read-only acceptance | Database and WAL hashes unchanged before/after backend and GUI review; review worker stopped |
| Native GUI | Real withdrawn Tk widgets displayed both owner-session pages and opened all 21 citations; synthetic fixture also exercised Previous/Next and end-of-session controls |
| Visible GUI inspection | Not completed: required Computer Use `node_repl` runtime unavailable; automated widget acceptance is not visual acceptance |

These are new measurements, not replacements for the earlier 89-test checkpoint
or its evidence. Local final results are preserved in ignored
`reports/LOCAL_VERIFICATION_ARTIFACT`,
`reports/LOCAL_VERIFICATION_ARTIFACT` and
`reports/LOCAL_VERIFICATION_ARTIFACT`. The explicit acceptance
script is [check_qualification_review.py](../scripts/check_qualification_review.py).
It does not launch Codex or write investigation records. No new authenticated
workload was needed, and the protected engine/configuration/authentication were
not changed or invoked.

A fresh standalone temporary-directory diagnostic again reported a restricted
token, no APM imports and no ACL changes. Direct `mkdir(0700)` and stdlib temporary
directories could be created but denied child writes/scans/removal; inherited
`mkdir(0777)` fixtures succeeded. This supports an environment/access-control
explanation, not an APM runtime regression. The process-local compatibility runner
does not turn the failed standard command into a pass. No security controls were
weakened. A development-only test connection cleanup error was corrected before
the final results above.

Read-only review uses an in-memory copy up to 256 MiB of SQLite pages, with
60-second copy and initial verification bounds. It is a fixed snapshot, not a live
view; reopening refreshes it. SQLite can coordinate live WAL readers through
shared-memory sidecars. Same-item final-outcome conflicts are a limited inference;
missing turn boundaries and other contradictions may remain unknown. Unkeyed
hashes do not authenticate event sources, accounts or command attribution, and
this feature does not provide bidirectional cooperation.

The [distribution assessment](DISTRIBUTION.md) records installed tools, source
packaging gaps and executable/installer/wheel/release acceptance requirements.
No downloadable product was built or published.

Relative to the published checkpoint, five files were added:
`apm/storage/review.py`, `apm/ui/qualification_window.py`,
`scripts/check_qualification_review.py`, `tests/test_review.py` and
`docs/DISTRIBUTION.md`. Eight existing files were updated:
`apm/storage/memory.py`, `apm/ui/main_window.py`, `apm/observatory/cli.py`,
`README.md`, `docs/ARCHITECTURE.md`, `docs/ENGINEERING_PROGRESS.md`,
`docs/OBSERVATORY.md` and `docs/WORKSTATION_CAPABILITIES.md`. The local content
audit covered these 13 files and resolved 51 local Markdown links; scans found
no credential patterns or owner-session identifiers in these source/doc changes.
Generated acceptance/test reports remain ignored. This was a local content audit,
not authorization or a staged audit for a future publication.

**Next proposed at the native-review checkpoint (superseded by the capsule mission below):** introduce tested per-user data defaults for installed APM
while preserving source-workspace defaults and explicit evidence paths; then
build a local Windows x64 one-folder bundle and developer wheel using an isolated,
pinned toolchain. Complete visible review inspection and clean-machine artifact
tests before claiming GUI/distribution acceptance. Do not add a bidirectional
instruction channel or publish artifacts under this local-only checkpoint.

## Beyond the Microscope: offline evidence and comparison — 2026-10-10

Phase 0 reconciled the actual workspace against the previous local review audit:
its 13 source/document fingerprints matched before new work. PR #1 was still open
with its original four commits and unchanged head/base. The protected executable's
read-only SHA-256 matched the retained qualification hash; it was not invoked.
The existing packaging assessment was reused; no tool/dependency was installed.

Phase 1 is preserved and verified. The retained successful owner session again
passed the existing read-only acceptance harness: 108 records in pages 100 + 8,
five Codex reports, one failed-command report, one completed-turn report, 81 host
process-generation records and 68 child records. Both saved investigations and
all 21 citations resolved against the recorded final chain tip. Database/WAL
hashes remained unchanged and the worker stopped. The owner evidence was not
exported, and no new authenticated Codex workload was run. Result:
`reports/LOCAL_VERIFICATION_ARTIFACT` (ignored).

Phase 2 now has working [Evidence Capsules v1](CAPSULES.md): a versioned closed
JSON schema, selected-session export, explicit redaction/disclosure, two internal
SHA-256 checks, optional external file-digest check, isolated read-only import,
cross-page citation lookup and a native viewer. Minimal disclosure excludes free
text and human records by default. Findings retain algorithm/window/truncation
metadata. Source declarations and original fingerprints are not elevated to
authenticated provenance. All archives are rejected; no extraction path exists.

An initial Phase 3 slice compares two explicitly selected sessions using exact
source/class/task groups and reported outcomes. It supplies scoped supporting
citations, alternatives, unknowns and proposed checks, flags incompatible outcomes
within a declared item/turn, and retains INSUFFICIENT EVIDENCE for a shared cause.
Synthetic and reported classes are separated. This does **not** implement persistent
semantic patterns, human-validated adaptation, causal discovery or multi-agent
cooperation. The [architecture map](COGNITIVE_ARCHITECTURE.md) and
[standards ADR](decisions/0001-capsules.md) distinguish these later gates.

### Final verification

| Check | Result |
|---|---|
| Required standard suite | 112 tests in 57.979 s; 1 failure, 97 error entries; existing restricted-token temporary-directory failure pattern |
| Compatibility suite | 112 tests passed in 75.011 s; zero failures/errors/skips |
| New capsule tests | 14 tests covering round-trip/disclosure, independent stdlib digest verification in an isolated interpreter, copy-returning read-only context, source preservation, opt-ins/redaction, tampering and external digest, rehashed structural lies, malformed JSON/archives, missing references, bounds/no overwrite, comparisons/false matches, native paging/citations, schema correspondence, inert instruction text, oversized sessions, synthetic separation and controlled CLI errors |
| Original native review | Complete owner session and 21 citations passed as above; no original database changes |
| Visible inspection | Still unavailable: no Computer Use `node_repl` runtime; actual withdrawn Tk widgets are automated acceptance only |

Final logs are `reports/LOCAL_VERIFICATION_ARTIFACT` and
`reports/LOCAL_VERIFICATION_ARTIFACT`; earlier interim measurements
were retained. The standard failure remains a real failed command, not a pass
renamed by the compatibility runner. No ACLs, global Python settings, global
agent configuration or protected dependencies were changed. Existing standalone
tempdir diagnostic evidence remains applicable; new capsule tests use fresh
ignored inherited-access fixtures.

### Synthetic round-trip and resource evidence

The final `scripts/capsule_demo.py --records 996` run created two synthetic sessions
with 1,998 total SQLite records. Each exported capsule contains 998 records and
explicitly omits one human-opinion fixture. The two primary files are 683,320 and
684,427 bytes. A fresh process verified the first capsule against its retained
file digest; the independent stdlib digest implementation is covered separately
by the unit suite. The original synthetic database hash was unchanged.

Native widgets visited nine 100-record pages and one 98-record page, opened all
99 saved citations and rendered the two-session comparison. It found the designed
shared outcome group and one within-session contradictory group. Matching evidence
references resolve to their respective capsules; the result still states
INSUFFICIENT EVIDENCE for a shared cause. The saved finding retains its original
last-100 inspection scope; export does not claim that finding inspected all 998
records. Visible GUI acceptance remains unverified.

Six timed exports and six imports (three per session, with Python `tracemalloc`
enabled) measured median export 2.455 s and import 0.240 s. A separate comparison
took 0.0189 s. Python-traced peak allocation was 9,554,755 bytes; sampled process
RSS ranged from 29,294,592 to 47,239,168 bytes. These are different metrics: native
SQLite allocations are excluded from Python tracing, and sampled RSS is not a
guaranteed peak. The workload used Python 3.14.7 on Windows AMD64, 12 logical CPUs
and approximately 63.4 GiB reported RAM, with local repository storage. Storage
hardware/cache behavior was not separately qualified. This is a small synthetic
measurement, not operational Codex throughput, a clean-lab benchmark or a latency
guarantee. Broader observation/recovery measurements from earlier checkpoints are
not replaced by these capsule timings.

Local artifacts and aggregate results are retained under
`reports/LOCAL_VERIFICATION_ARTIFACT`; the command log
is `reports/LOCAL_VERIFICATION_ARTIFACT`. This directory contains the actual
synthetic capsules, comparison output and verification metrics, all ignored by Git.
Earlier 120-record and interim 996-record measurements remain preserved separately.

### Local changes and remaining work

Added `apm/evidence/{__init__,capsule,compare,cli}.py`,
`apm/ui/capsule_window.py`, `tests/test_capsule.py`, `scripts/capsule_demo.py`,
`schemas/evidence-capsule-v1.schema.json`, `docs/CAPSULES.md`,
`docs/COGNITIVE_ARCHITECTURE.md` and `docs/decisions/0001-capsules.md`.
Updated the CLI and main-window entry points, `.gitignore`, README, ROADMAP,
SECURITY, architecture and this progress document. The new capsule extension is
ignored so local exports cannot be accidentally staged through ordinary Git use.
No source history, existing evidence or old formats were rewritten. All changes
remain local and uncommitted; no branch/ref, PR, repository setting or release
was changed.

Important limits: capsules are unsigned, limited to 1,000 source-session records
and 4 MiB, and cannot reverify the original chain from redacted receipts. Their
checksums do not prove identity, truth, completeness or legal custody. Imported
clock uncertainty remains unknown. Comparison labels are deterministic clues,
not proof of the same command or cause. Full semantic memory, forensic adapters,
federation, provider cooperation, signing/key management and downloadable products
remain unimplemented. No private keys, provider credentials or paid API calls were
used. The existing source-only Windows launch route remains the tested delivery.

**Next exact task:** implement an append-only hypothesis and human-review journal
separate from raw observations. Bind each claim/review to capsule digests and
resolvable supporting/contradicting references; preserve alternatives, missing
evidence, correction history and INSUFFICIENT EVIDENCE. Test stale/missing citations
and prove that approving a hypothesis neither edits source evidence nor grants
execution authority. Human-reviewed semantic pattern promotion follows that
boundary; packaging remains the independent later track described in
[DISTRIBUTION.md](DISTRIBUTION.md).

## Holmes Protocol checkpoint — 2026-10-10

### Baseline and preservation

Before edits, all 19 files in the prior capsule audit matched their recorded
SHA-256 values. The two integration source files were copied into a new ignored
baseline directory before modification. Existing pending work was preserved.
The root remains `main` at `717aaa50c592d92e7369711567374c5c801f7f2b`.
A read-only GitHub check found PR #1 open and unmerged, with four commits and head
`ab019da0d2c970efab80fe4878b7f2ec55cb9370`. No Git ref, commit, index, remote,
repository setting or release was changed. Current Holmes extensions remain local.

The protected executable's SHA-256 matched the retained owner qualification at
baseline. No Codex executable was launched; no installation, supporting component,
authentication, global configuration, plugin or MCP setting was modified. The
historical authenticated workload was reused, not repeated.

### Working implementation

Added the `apm.holmes` package: bounded capsule-reference catalog, schema-1
append-only SQLite journal, deterministic skeptical challenges, HTML/JSON reports,
versioned exact-match pattern retrieval and an offline assessment protocol.
Hypotheses retain supporting/contrary citations, alternatives, missing evidence,
proposed checks, uncertainty, declared producer and review state. Exact retries
deduplicate; conflicting requests and stale revisions fail. Corrections, rejection,
supersession and claim revisions preserve prior states. An interrupted transaction
recovers the committed prefix. Backup uses a new destination and verifies its chain.

The functional native Holmes Lab opens journals and multiple capsules, stages
support/contradictory records, creates hypotheses, resolves saved references,
generates challenges, records/corrects assessments, reopens full history, retrieves
reviewed patterns and exports reports. File/SQL work uses one worker and bounded
submission. The ordinary Genesis, Memory/Ask, qualification and capsule windows
remain present. Report checks and history share one snapshot, including under a
concurrent writer. Reports escape HTML and contain cited metadata rather than raw
source sessions. Neither human review nor a proposed check grants execution rights.

Pattern activation requires a supporting review and a matching, resolvable example.
Explicit source/class requirements prevent mixing synthetic and reported cases.
Versions, retirement/reactivation and review provenance persist; an adverse later
review suspends matching. Synthetic review fixtures cannot activate patterns for
real evidence classes. Pattern administration remains a Python API, with retrieval
in the GUI. A general validation registry and promotion editor are not implemented.

After journal/widget checks passed, a bounded provider-neutral response contract
and synthetic two-role demonstration were added. Scope, citations, duplicate IDs,
byte/time/token declarations and authority fields are validated. This is not a
real two-agent/model workflow, provider integration or authenticated communication.

### Verification

| Check | Current observed result |
|---|---|
| Documented compatibility runner | **130 tests passed**, 84.500 s, no failures/errors/skips |
| Unmodified standard unittest command | **130 tests**, 67.548 s, **1 failure and 97 error entries** |
| New Holmes coverage | 18 tests cover scope/invalid citations, duplicate/stale requests, append-only history, correction/rejection/supersession, interruption, backup/tamper checks, snapshots, source preservation, reports, patterns, offline assessment validation and native widgets |
| Fresh Python process | Two synthetic capsules opened, opposing citations resolved, hypothesis/challenge/review/correction appended, four revisions reopened, backup tip checked, new HTML/JSON reports produced |
| Independent parent check | Recomputed journal SHA-256 chain without the Holmes verifier; source database and both capsule hashes unchanged |
| Native Holmes widgets | Actual withdrawn Tk widgets exercised creation, opposing references, saved citation lookup, challenge, review/correction, report, reopen, history selection and pages of 100 + 5 records; worker threads stopped |
| Labeled pattern fixture | 1 true positive, 6 true negatives, 0 false positives/negatives; additional counterexample, optional-difference and retirement/correction tests passed. This tiny fixture does not establish operational accuracy |
| Retained owner review | 108 integrity-verified records; 5 public reports, 1 reported failure, 1 completed turn, 81 host process and 68 child-generation records; pages 100 + 8; 21 citations opened; expected tip matched; database/WAL unchanged |
| Visible/manual GUI acceptance | **UNVERIFIED**: required Computer Use runtime unavailable; automated widgets are not visual approval |

The standard command's environmental failure pattern remains distinct from the
compatibility pass. A new diagnostic, with no APM imports, again found a restricted
token: `os.mkdir(0700)` and `tempfile.mkdtemp` allowed creation but denied child
writes/scans/removal, while inherited `0777` directory operations passed. No ACL,
global security policy or Python configuration was changed. The compatibility
runner changes only its process-local fixture directory creation within APM.

Two defects found during development were fixed before final verification: an
unclosed SQLite handle in a test cleanup, and a pattern optional-difference counter
that incorrectly passed mapping values to `Counter.update`. These were test/application
defects, respectively, not attributed to the Windows temporary-directory issue.
Interim logs are retained; final measurements above supersede no historical result.

Local evidence (ignored, not publication candidates):

- `reports/LOCAL_VERIFICATION_ARTIFACT`
- `reports/LOCAL_VERIFICATION_ARTIFACT`
- `reports/LOCAL_VERIFICATION_ARTIFACT`
- `reports/LOCAL_VERIFICATION_ARTIFACT`
- `reports/LOCAL_VERIFICATION_ARTIFACT`
- `reports/LOCAL_VERIFICATION_ARTIFACT`

The fresh child measured 0.987 s for its journal/review/reopen/report/backup interval
on the existing Python 3.14.7 Windows AMD64 workstation. This is one sample with two
three-record synthetic capsules and four journal entries, excluding fixture creation,
parent verification and the subsequent cooperation fixture. HTML was 35,330 bytes
and JSON 36,747 bytes; each contained two cited records and four revisions. No RAM
peak, maximum-size stress test or operational throughput is claimed.

### Changed files, limits and exact next step

New files: `apm/holmes/{__init__,model,journal,challenge,report,patterns,cooperation,cli}.py`,
`apm/ui/holmes_window.py`, `scripts/holmes_demo.py`, `tests/test_holmes.py`,
`docs/HOLMES.md`, and `docs/decisions/0002-holmes-journal.md`.
Integration edits: `apm/__main__.py`, `apm/ui/main_window.py`.
Updated README, ROADMAP, LIMITATIONS, SECURITY, architecture, cognitive architecture,
distribution, workstation capabilities and this progress record. No observation,
memory, qualification-review or capsule implementation file was rewritten.

Remaining limits include unauthenticated producer/reviewer declarations, unkeyed
integrity, unknown collection completeness/clocks, no proven command attribution or
causation, heuristic claim analysis, bounded journals/capsules, no real provider
cooperation, no visible human GUI acceptance and no tested distributable product.
Packaging probes still find PyInstaller 6.22.3 and WiX 7.0.0 outside the APM venv;
no tools were installed and no artifact was built. BUILD, INSTALL, packaged LAUNCH,
UNINSTALL and installer DATA PRESERVATION remain UNVERIFIED as listed in
[distribution gates](DISTRIBUTION.md).

**Next exact engineering task:** add a native pattern promotion/validation workflow
that records labeled validation episodes and counterexamples before activation,
with explicit review provenance and false-match results. This closes the main
remaining usability gap in the tested interpretation-to-pattern loop. Owner-visible
Holmes acceptance remains a separate pending qualification, not a claim this tool
session can make. [User/API guide](HOLMES.md).
