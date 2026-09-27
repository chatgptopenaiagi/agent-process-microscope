# Replay model

Replay is passive inspection of a recorded session. It does not repeat commands, recreate files, contact an agent, or start observation adapters. Event targets and evidence references remain text.

## Session files

| File | Purpose |
| --- | --- |
| `session.json` | Session identity, mode, scope, lifecycle, limits and checkpoints |
| `events.jsonl` | Canonical event stream used by replay |
| `derived_states.jsonl` | State summaries saved while the session was recorded |

[`read_session`](../apm/storage/reader.py) reads `session.json` and `events.jsonl`. It does not trust or load `derived_states.jsonl` to drive replay. The UI starts a fresh `StateEngine` when a replay is loaded or reset and feeds every replayed event through it.

Events are sorted by their timezone-aware timestamps; original file order is the stable tie-breaker for equal timestamps. Live recording normally already follows this order. If externally supplied or altered events are out of timestamp order, replay's reconstructed order can differ from their original dispatch order. Reconstructing state is not authenticating the recording.

## Opening and playback

Choose **Open session…** or use the CLI `replay` entry point. If observation is running, the GUI requests a stop and waits for recorder shutdown before loading the session. The header changes to **REPLAY PASSIVE**. No new recording is created by playback.

The controls offer **Play replay**, **Pause replay**, **Reset replay**, **Leave replay**, and speeds **1×**, **4×**, and **Instant**. Timed playback follows recorded time differences. Instant consumes at most 200 events per UI tick; it does not skip early events to jump to the final visible rows. All accepted events therefore contribute to reconstructed state, while the visible timeline retains at most 2,000 rows.

Pause affects playback progression. Filters and **Clear view** affect presentation only. Reset starts the recorded sequence and state reconstruction again. Recorded synthetic events remain labelled as demo evidence; replay does not turn them into live observations.

## Bounds and validation

The reader enforces these Genesis limits:

| Input | Limit or check |
| --- | --- |
| `events.jsonl` | 64 MiB, including a check against growth while reading |
| `session.json` | 256 KiB metadata limit |
| Event line | 256 KiB |
| Loaded events | 100,000; an additional event produces an omission warning |
| Identity | UUID session/event IDs, matching session membership, no duplicate event IDs |
| JSON and fields | No duplicate keys or non-finite numbers; canonical runtime validation |
| Selected files | Reject symlinked session files and resolved files outside the selected session directory |

These limits bound input handling; they are not a complete hostile-filesystem sandbox or cryptographic verification. The reader holds the accepted event list in memory, so the 2,000-row display bound is not a claim that only 2,000 events are loaded.

## Interrupted recordings

An open lifecycle status at the last checkpoint produces a warning: the session may still be active or may have been interrupted. It does not prove either condition.

An invalid, unterminated final event at actual end-of-file can be omitted with a warning while preceding valid events are recovered. Invalid completed lines, identity mismatches, and malformed earlier events fail validation. A valid final JSON event without a newline remains readable. Recovery does not edit or repair the original files.

Session metadata can be older than the final retained event after interruption. Warnings, incomplete coverage, and drop counts should accompany any conclusion drawn from such a replay.

## Provenance remains visible

Imported Codex events retain `imported_codex_report` provenance and import-time timestamp basis in metadata. Replay timing cannot reconstruct unavailable original execution timing. **Raw event** shows the sanitized canonical representation, not the original JSONL export or raw terminal stream.

Replay uses the current state-engine rules. A later release could reconstruct summaries differently from a historical `derived_states.jsonl`; Genesis does not pin a separate state-engine version inside each event. The canonical evidence and its provenance remain the basis for inspection.

See [Event model](EVENT_MODEL.md), [Observability model](OBSERVABILITY_MODEL.md), and [Validation](VALIDATION.md).
