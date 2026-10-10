# Living Observatory engineering checkpoint

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

**Next exact task:** implement a read-only qualification review in native Memory /
Ask that pages the entire selected session, resolves saved finding citations and
shows independent host evidence beside agent reports, while explicitly identifying
unknown account identity and command-to-PID attribution. Validate it against a
sanitized synthetic fixture and the locally retained successful session without
modifying that recording; complete visible native GUI inspection before adding
any bidirectional instruction channel.
