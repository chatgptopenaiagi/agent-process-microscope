# Adapter model

Adapters translate a bounded external source into payload dictionaries. They do not produce trusted canonical events themselves. The central normalizer applies session identity, redaction, defaults, and validation before normal recording or presentation.

[`ObserverAdapter`](../apm/adapters/base.py) exposes `poll() -> list[dict]` and `close()`. `close()` stops observation; it does not own or terminate an attached workload. Genesis adapters are synchronous pollers used by a single collection worker, not independently scheduled background services.

## Implemented adapters

| Adapter | Scope and output | Default bounds and limitations |
| --- | --- | --- |
| `ProcessObserver` | Explicit root PID and verified descendants; identity, name, lifecycle and resource metadata | 256 tracked processes and a 0.5-second scan budget; polling can miss short-lived processes |
| `FileSystemObserver` | Metadata for allowed files beneath the selected workspace | 5,000 files, 12,000 entries, 0.5-second scan budget and 256 change events per poll |
| `GitObserver` | Selected workspace's repository status and staged/unstaged line counts | Five-second shared probe deadline, 1 MiB per helper output stream and 128 records per parsed list |
| `SystemObserver` | Whole-machine CPU, RAM, disk and network counters/rates | First rates/CPU require warm-up; unavailable metrics carry reasons; GPU is not probed |
| `CodexAdapter` | Explicitly selected, finite `codex exec --json` export | 64 MiB file, 1 MiB input line, 100,000 lines and 100 lines per poll |

Bounds constrain the implemented work, but they are not hard operating-system real-time guarantees. A system call can still delay a polling function. Bound exhaustion is surfaced rather than silently represented as complete coverage.

## Process scope and command prefixes

The process observer records PID plus creation time and checks identity before trusting a reused PID. The attached root's first observation is `OPEN`; a newly discovered descendant is labeled `START` with metadata explaining that this is first observation, not an exact start event. Disappearance produces a stop report with an unknown exit code. The observer does not call `wait()` on or terminate the attached workload.

The root process's arguments are omitted. Selected descendants may expose only a recognized tool prefix: names such as `pytest`, `ctest`, `ninja`, `cmake`, `git`, and `msbuild`, or a narrow Python `-m` prefix. Remaining arguments, inline code, selectors, and prompts are omitted. The state engine can recognize more direct runner forms from an explicit imported command report than attach mode itself collects. Shell wrappers are not expanded or executed to discover their meaning.

Descendancy proves an observed relationship, not intent or responsibility for nearby filesystem/network activity.

## Workspace and Git observations

Filesystem scans use metadata rather than file contents, exclude designated sensitive/cache paths and the session output root, and avoid following unsupported workspace links. A complete snapshot establishes the comparison baseline. An incomplete scan retains the prior complete baseline rather than interpreting missing entries as deletions. Changes exceeding the per-poll event limit are reported as omitted; they are not promised for later replay. Rename-like changes can appear as separate creation and deletion.

Git observation is optional: an unavailable Git executable or repository produces an unavailable report. It uses `shell=False`, bounded stdout/stderr, a shared deadline, and hidden helper windows on Windows. The observer disables optional locks, prompts, hooks, fsmonitor, external diff, text conversion, and configured clean/process filters for its commands. It requests metadata, not patch text. Its status and diff commands are separate observations, not an atomic repository transaction.

Only an APM-owned Git helper may be terminated to enforce its timeout. The attached process tree is not killed. These guards are implemented precautions, not a general sandbox for arbitrary hostile repositories or native Git defects.

## Explicit Codex import

The importer is an allowlist reader for a user-selected JSONL export. It does not find an existing Codex session, read private rollout/authentication stores, attach to a live Codex transport, or make a model call. Unsupported message types and private-content fields are excluded. Command reports and permitted file-change metadata retain imported-report provenance.

The adapter snapshots the input file's initial extent and finishes; it does not continuously tail later appends. Its timestamps identify import time when original timing is unavailable. The original export remains untouched and may contain content deliberately excluded from the APM session.

The CLI import pipeline directly normalizes, records, and derives state. It bypasses the live event bus and test interpreter. A recognized imported command may therefore yield `TESTING` state without a separate inferred test event. See [Codex integration](CODEX.md) for the exact supported protocol subset.

## Extending an adapter

A new adapter should declare its evidence source, scope, unavailable conditions, polling limits, and ownership before adding new event types. Return payload dictionaries and pass them through the normalizer. Preserve provenance and evidence references; avoid upgrading reports into independently verified facts.

Tests should cover scope escape, malformed input, unavailable evidence, redaction, bounded work, shutdown, and side effects appropriate to the source. Tests for future adapters are requirements for their implementation, not claims that those adapters already exist. Browser/Joomla observation, managed agent launch, GPU probing, and remote/cloud transports remain deferred.
