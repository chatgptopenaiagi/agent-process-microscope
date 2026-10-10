# Local observatory: implemented vertical slice

This experimental extension preserves Genesis's Python/Tk observers and JSONL
recordings. New live/demo sessions additionally write `sessions/observatory.sqlite3`
(or the selected sessions directory). Old recordings are not migrated or edited.
The receiver, companion and history viewer are independently startable. Nothing
opens a listening socket merely by starting the normal GUI.

## Architecture decision, 10 October 2026

These are engineering judgments, not comparative performance measurements.

| Candidate | Complexity, installation, maintenance | OS, accuracy, overhead | Security and extensibility |
|---|---|---|---|
| In-process Tk + JSONL/SQLite only | Smallest deployment, no additional dependency | Portable Python; retains Genesis evidence limits; no IPC cost | Small exposure, but no independent companion or scoped external investigation |
| Tk + SQLite WAL + authenticated loopback companion **chosen** | Standard library plus existing psutil; small protocol to maintain | Windows native validation; other OSs unqualified; receipt order and provenance explicit; bounded IPC and transactions | Session-scoped reader/reporter capabilities; no remote bind or execution API; adapters remain replaceable |
| Windows named pipes + SQLite | Native ACL/peer-identity integration and Windows tests needed | Strong Windows integration; separate transport needed elsewhere; performance unmeasured | Potential stronger OS identity boundary; default pipe permissions still require review |
| Web/gRPC service + PostgreSQL + browser GUI | Extra service, packages, runtime, migrations and packaging | Suitable for future multi-host/multi-writer use; no measured need here | More endpoints and deployment controls; broader language ecosystem |

[SQLite WAL](https://sqlite.org/wal.html) supplies concurrent readers with serialized
writes on local storage. [PostgreSQL MVCC](https://www.postgresql.org/docs/current/mvcc-intro.html)
is an established alternative when independent writers justify a server. JSONL
alone remains easy to inspect but needs repeated scans for cross-session queries.
SQLite is the new canonical memory; Genesis JSONL remains an independent legacy
recording. Their writes are **not** one distributed transaction. A SQL error stops
collection visibly, closes the JSONL recording, and does not terminate the specimen.

[Named-pipe security](https://learn.microsoft.com/en-us/windows/win32/ipc/named-pipe-security-and-access-rights)
requires deliberate permissions. Localhost also requires authentication. This
prototype chooses capability credentials and explicitly does not claim protection
against another process able to read the owner's capability files or database.

## Run and inspect

From the repository root, using its isolated venv:

```powershell
.\.venv\Scripts\python.exe scripts\observatory_demo.py
.\.venv\Scripts\python.exe -m apm memory .\sessions\observatory.sqlite3 --operation gui
```

The first command creates an ignored `reports/observatory-native-UUID/` directory,
executes a deliberately failing native unittest workload, runs the receiver as a
separate hidden process, sends the runner's actual exit report, reopens SQL,
investigates, records a human-style validation note, and backs up. The note is
script-generated validation data; it does not authenticate a human. This is **not
a Codex model run**. The second command opens memory after a normal observation
has populated it; use the demo's printed database path to inspect that fixture.
The normal GUI also has **Memory / Ask…**. Select a session, browse/search pages,
watch arrivals, ask for a local evidence review, select an event and record an
opinion. SQL work runs outside the Tk event loop. Pages contain at most 100 rows.

For separate external clients:

```powershell
.\.venv\Scripts\python.exe -m apm memory-init .\sessions\bridge-example
.\.venv\Scripts\python.exe -m apm serve --config .\sessions\bridge-example\receiver.key --database .\sessions\observatory.sqlite3 --duration 300
# Another terminal; this investigator receives only the selected session:
.\.venv\Scripts\python.exe -m apm query --capability .\sessions\bridge-example\reader.key
```

`memory-init` refuses an existing directory. Give a producer only `reporter.key`
and an investigator only `reader.key`; `receiver.key` contains both grants.
Files inherit filesystem access rules and are plaintext. The CLI passes paths,
not credential values, on command lines. Up to 32 grants can be explicitly
configured, each with one session and one role. The receiver duration is 1–3600
seconds. Add `--pid PID --workspace PATH` to explicitly observe a selected process
alongside one common session scope. Omitting both starts only the receiver.

`feed-codex --capability PATH --outbox PATH --port 47631` consumes stdin from an
**explicitly authorized public `codex exec --json` stream**. It does not discover
or attach to private histories. The protected workstation executable is
`C:\Program Files\OpenAI\Codex\0.156.0-alpha.17\codex.exe`; normal APM observation
does not launch, install, configure or substitute it. An operator may pipe an already-authorized
exec invocation into the companion. Do not add an unreviewed model command just
to obtain telemetry. The finite Genesis `import-codex` remains unchanged.

For the explicitly owner-authorized engineering qualification, the separate
[`scripts/qualify_codex.py`](../scripts/qualify_codex.py) test harness creates a new
ignored disposable workspace and invokes exactly that protected executable with
`exec --json --ephemeral`, read-only command sandbox and no approval escalation.
It inherits the existing authentication/configuration route without inspecting or
copying credentials, changing persisted configuration, or bypassing rules. The
selected task is one deliberately failing unittest using APM's existing venv.
This is an explicit workload launcher, not a new execution operation in the APM
receiver or GUI. Its default workload bound is 45 seconds (maximum 120).

Raw stdout feeds the existing allowlisting companion directly. Raw stderr is
discarded after in-memory matching to fixed operational labels; labels do not
establish the fatal error or authentication state. The observer stops before the
harness cleans up only its owned PID/birth-time generations. A fresh process
reopens and verifies SQL, and real withdrawn Tk widgets browse evidence and save
Ask. These automated widget checks are distinct from visible human inspection.
An empty stream or lifecycle-only failure cannot qualify the command workload.
See the [qualification evidence](ENGINEERING_PROGRESS.md): an owner-run engineering
slice passed while attempts under the restricted development identity failed before
public reports. Account identity is not independently verified in either context.

After interruption, use the same outbox with `--retry-only`. Keep its capability
and session stable. The outbox stores sanitized canonical events, stable IDs and
sequence numbers before sending. Acknowledgments follow database commit. A lost
ack causes safe duplicate delivery; changed duplicates are rejected. A full
outbox stops consumption, retains a loss count, and sends an unavailable marker
when space/connectivity recover. Later unconsumed source activity is unknown.
An idle stdin feed waits for its producer; EOF or Ctrl+C ends it. Closing a pipe
can affect a producer's output handling; this is not transparent attachment.

Other local operations (use an actual session UUID):

```powershell
.\.venv\Scripts\python.exe -m apm memory .\sessions\observatory.sqlite3
.\.venv\Scripts\python.exe -m apm memory .\sessions\observatory.sqlite3 --operation ask --session SESSION_UUID
.\.venv\Scripts\python.exe -m apm memory .\sessions\observatory.sqlite3 --operation events --session SESSION_UUID --search unittest --after 0
.\.venv\Scripts\python.exe -m apm memory .\sessions\observatory.sqlite3 --operation verify
.\.venv\Scripts\python.exe -m apm memory .\sessions\observatory.sqlite3 --operation backup --destination .\sessions\new-backup.sqlite3
```

`ask` persists the local finding; external `query --operation investigate` is
read-only. A note can record annotate/approve/reject/investigate/correct and up
to 20 same-session evidence references. None of these execute or authorize work.
Backups use SQLite's online backup API and refuse destination overwrite. `events`
exports one JSON page; continue using the last `arrival` as `--after`.

## Protocol and evidence contract

Protocol 1: one TCP connection, one request/response, 4-byte unsigned big-endian
length followed by JSON. Bind is fixed to `127.0.0.1`. Request fields are exactly
`version` (integer 1), `credential`, `operation`, `params`. Duplicate JSON keys,
nonfinite numbers, unsupported versions and unknown operation fields are rejected.
Failures return `{version:1, ok:false, error:"request_rejected"}` without raw data.

| Operation | Role | Parameters |
|---|---|---|
| append | reporter | event, stream UUID, sequence |
| append_batch | reporter | entries: 1–32 append parameter objects, atomic |
| events | reader | optional after, limit, search; scope comes from capability |
| investigate | reader | none; last 100 receipt-ordered records |
| health | reader | none; aggregate receiver delivery counters and selected scope |

Every `event` contains exactly the existing [Genesis fields](EVENT_MODEL.md).
Unknown top-level fields are rejected. Genesis metadata redaction still applies;
the Codex source additionally uses its strict item/field allowlist. The stored
envelope adds protocol version, stream/sequence, receiver UTC, origin, capability
label, evidence class and `missing_before`. Capabilities authenticate access, not
the truth or process identity of a report. External clients cannot set host origin.
Unknown metadata is not a compatibility extension to the top-level protocol.

OBSERVED denotes trusted local host observation; AGENT_REPORTED denotes accepted
producer claims; INFERRED, SYNTHETIC, UNKNOWN and UNAVAILABLE retain their separate
meanings. HUMAN_RECORDED identifies a local decision record with unverified human
identity. An external reporter may describe an inference or synthetic fixture,
but cannot elevate it to an independent host observation. CONFLICTED is not yet a
stored state; conflicting duplicate delivery is rejected.

Codex exec timestamps are client receipt times, explicitly labelled; origin
execution times are unavailable in this subset. Sequence is per durable producer
outbox. SQL arrival is local commit order, not a global execution clock. Host
process PID/start-time pairs remain in Genesis metadata. No automatic PID-to-Codex
thread binding, causal attribution, Lamport clock or cross-host clock comparison
is implemented. Same-session queries co-locate evidence; they do not prove causality.

## Memory and temporal integrity

Schema 1 has `records` (arrival, unique event ID, session, stream, sequence, body,
previous fingerprint, fingerprint) and `counters` (logical count/bytes). Indexes
support session/arrival, event ID and stream/sequence. Findings and decisions are
additional records with evidence references. There is no silent evidence editing,
SQL endpoint, graph database or speculative table for every proposed entity.
Initialization checks application ID and schema version. Unknown schemas and
foreign populated databases are refused. Future schema migrations require new
tests; none beyond initial creation is claimed.

Canonical bytes are Python JSON with sorted keys, compact separators, ASCII
escapes, finite numbers and no Unicode normalization. This is an explicit APM
profile, **not** an implementation of [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785).
[MessagePack](https://msgpack.org/) and [Protocol Buffers](https://protobuf.dev/overview/)
are plausible compact encodings; they add dependencies or schema-generation work.
JSON fits the existing adapter and audit workflow. No encoding speed superiority
has been measured.

`H_i = SHA256(b"APM-memory-v1\0" || bytes.fromhex(H_(i-1)) || canonical(envelope_i))`.
The initial previous hash is 64 zero hex digits. The envelope excludes its own
hash. One chain orders SQL receipts while stream sequences preserve producer
order and expose gaps. Verification checks SQL integrity, chain, indexed identities,
sequence/gap consistency and counters inside one read snapshot. Save a tip outside
the database and pass `--expected-tip` to detect a changed tail. An attacker able
to rewrite the whole database can recompute an unkeyed chain. Hashes do not prove
authenticity, complete observation, execution, intent or causality.

## Bounds and security

| Resource | Bound |
|---|---|
| Request / response | 64 KiB / 4 MiB |
| Event input | 32 KiB before sanitization |
| Concurrent receiver handlers / waiting backlog | 4 / 4 |
| Frame receive deadline / send timeout | 3 seconds / 3 seconds |
| SQLite lock wait | 3 seconds |
| Atomic append batch | 32 events, still subject to request byte cap |
| Outbox default / maximum pending events | 1,000 / 10,000 plus an owed loss marker |
| Memory default logical cap | 100,000 records or 128 MiB canonical body bytes |
| Query page / investigation window | 100 records |
| Query text | 120 characters, parameterized literal substring |

Database/index/WAL bytes exceed logical body bytes. Short queries avoid long-held
WAL readers; no exact total disk ceiling or power-failure certification is claimed.
At capacity, archive and explicitly select another database; no automatic pruning
or deletion of user history occurs. API constructors allow bounded custom limits.
GUI session listing currently shows the 100 most recent sessions. Text search is
a bounded-corpus scan, not full-text indexing. No adversarial latency SLA is claimed.

Untrusted reports remain data. No interpreter executes their commands, paths,
recommendations or decisions. No TLS, OS peer identity or per-agent credential
rotation UI exists. Local plaintext capability/recording access is a material
trust boundary. Process observation remains scoped, metadata-only and passive.
Raw source stdout/stderr, reasoning, prompts and file contents are excluded.
Pattern redaction remains best effort. APM's observation transport is loopback-only;
the separately authorized qualification CLI may contact its configured provider.

## Dialogue, visualization and packaging boundaries

[Official exec documentation](https://learn.chatgpt.com/docs/non-interactive-mode)
describes public JSONL activity. [App-server documentation](https://learn.chatgpt.com/docs/app-server)
describes a separate application-owned protocol. Local version/help checks confirm
the protected CLI's exec JSON option; a bounded isolated probe also delivered real
public failure reports. A later owner-run operation passed the engineering evidence
checks documented in [the checkpoint](ENGINEERING_PROGRESS.md), without independently
verifying account identity or attachment to an existing ChatGPT conversation. APM's implemented
bridge is local deterministic Ask plus scoped machine-readable evidence queries.
No OpenAI API, MCP registration, provider integration or command-back channel is
implemented. An authorized agent can run the read-only query CLI without SQL or
process-control authority.

The useful 2D telescope is a session picker with evidence pages and cited findings;
the microscope remains the original event-detail GUI. Blender asset authoring,
Godot and Three.js are optional research candidates, not implemented modules.
Tk adds no runtime; a [Godot export](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_windows.html)
adds another application runtime; [Three.js](https://threejs.org/manual/) adds a
browser integration surface. Blender would be an offline asset tool, not a live
observer. Its requested manual page was unavailable during this research, so no
Blender compatibility claim is made. There is no evidence that 3D improves this
failure investigation.

[PyInstaller's bundle modes](https://pyinstaller.org/en/stable/operating-mode.html)
are a possible future packaging route. A one-folder portable bundle would make
dependencies inspectable; a one-file bundle adds runtime extraction; an installer
adds upgrade/uninstall obligations. None was built or clean-install tested here.
The existing `.venv` and `Launch-APM.pyw` remain the verified source launch route.

See [engineering evidence and next step](ENGINEERING_PROGRESS.md),
[AEGIS comparison](research/AEGIS-COMPARATIVE-ANALYSIS.md), and
[capability register](WORKSTATION_CAPABILITIES.md).
