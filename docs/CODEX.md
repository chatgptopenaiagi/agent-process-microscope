# Codex observation boundary

APM imports an explicitly selected export from `codex exec --json`. It does not
start Codex, call a model, inspect authentication, or read private rollout/history
files. Attaching APM to a PID observes operating-system evidence only; that does
not supply a Codex event stream or reveal reasoning.

For an export the owner deliberately captured, run:

```powershell
.\.venv\Scripts\python.exe -m apm import-codex C:\Example\Exports\exec.jsonl --sessions .\sessions
```

This creates a sanitized APM recording. It does not modify or sanitize the
original export, which can still contain excluded content. Do not place raw
exports in version-controlled source folders.

The command is run from a source checkout; the export path is fictional.

## Supported source and research

OpenAI documents `--json` as a JSONL stdout stream with thread, turn, item, and
error events. It includes command executions and file changes, but also messages,
reasoning, and other content. APM therefore selects action metadata instead of
recording the source stream wholesale. The non-interactive documentation includes
the `command_execution` example used as the initial fixture shape.
[Official non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode).

The app server is a separate JSON-RPC integration with client initialization,
thread/turn operations, and notifications. Its slash-separated event names and
camelCase item schema are not this import format. The documented schema-generation
commands describe that protocol, not the exec JSONL schema. These sources did not
establish a general read-only attachment to an arbitrary existing CLI process.
APM does not open a server, expose a listener, send approvals, or resume a thread.
[Official app-server documentation](https://learn.chatgpt.com/docs/app-server).

Research on 2026-09-27 also inspected the locally installed public npm package
manifest and launcher, then the binary's `--version` and `exec --help` only.
The binary reported `codex-cli 0.156.1` and confirmed `--json` prints JSONL events.
Those two bounded hidden help processes used an isolated APM `CODEX_HOME`; no
model call, real session, authentication file, or credential was accessed.

## Adapter interface and retained fields

`apm.observers.codex.CodexAdapter(path)` exposes `poll() -> list[dict]`, `close()`,
`done`, and `counters`. The CLI passes payloads through the central Normalizer
before display, queueing, or storage. The adapter itself never writes output.

| Input | Retained metadata / canonical action |
| --- | --- |
| `thread.started` | Valid UUID thread ID; START |
| `turn.started`, `turn.completed`, `turn.failed`, `error` | Known event type only; START, STOP, FAIL |
| `item.started/updated/completed`, `command_execution` | `item_N` ID, known status, command string, integer exit code; START, UPDATE, STOP |
| Same lifecycle, `file_change` | ID, status, up to 100 `path` + `kind` entries; completed single successful add/update/delete maps to CREATE/WRITE/DELETE |

Other file-change phases map to UPDATE; failed/declined changes map to FAIL.
The file-change subset accepts string kinds `add`, `update`, `delete`. Unknown
variants fail closed rather than guessing; this is a deliberately narrow import
subset, not a claim of exhaustive version-specific schema compatibility.

Reasoning, agent/user messages, MCP arguments/results, plans, web-search content,
command output, diffs, environments, error text, usage, and arbitrary extra fields
are discarded. Unknown events produce a fixed unavailable reason without the
original type value or content. Known excluded items increment a counter without
producing an event. Secret-shaped command/path values are redacted centrally;
pattern redaction cannot guarantee removal of every possible secret in arbitrary
command text. Review selected exports and recorded sessions before sharing.

## Evidence and limits

An imported record proves what the selected file reports. It does not independently
prove the action occurred, attribute a workspace change to an OS PID, or establish
the exporter is authentic. Metadata labels `provenance=imported_codex_report` and
`timestamp_basis=import_time`; line order and source line numbers are retained.
Original execution times are not invented. Raw content is not copied into APM.

Default caps are 64 MiB/file, 1 MiB/line, 100,000 lines and 100 input lines/poll.
The importer reads only the initial regular-file snapshot. It ignores later
appends, rejects oversized input, reports malformed/truncated JSON, and accepts a
complete final JSON record without a trailing newline. Known private `.codex`,
`rollout-*`, auth, configuration, history, and session-index paths are rejected.
Renaming a private file does not turn it into an authorized export: select only
purposefully captured public exec output. No import path is auto-discovered.

Tests use synthetic records only and check passive behavior, forbidden-content
exclusion, central redaction, malformed input, bounds, snapshot behavior, and
private-path rejection. No real model run is needed for the importer tests.
