# Observability model

APM makes external work inspectable through a timeline, a conservative activity summary, system telemetry, and four views of the selected event. Evidence remains distinct from the interpretation drawn from it.

An attached process, a changed file, and a machine resource counter are different observations. Their proximity in time does not prove that the process caused the file change or consumed the measured whole-machine resources.

## What each source establishes

| Source | Evidence available in Genesis | What remains unproven |
| --- | --- | --- |
| Process attachment | Selected PID and verified descendants, PID/creation-time identity, sampled resource and lifecycle metadata | Exact process start time from first observation, exit code, intent, file/network causation, missed short-lived children |
| Filesystem polling | Metadata changes within the selected workspace, subject to exclusions and scan bounds | File reads, contents, responsible actor, changes that preserve observed metadata |
| Git polling | Workspace-scoped status and staged/unstaged line-count metadata | Patch contents, responsible actor, atomicity across separate Git commands |
| System sampling | Whole-machine CPU, RAM, disk and network counters/rates | Attribution to the selected agent; GPU metrics are unavailable |
| Explicit Codex JSONL import | Allowlisted reports from the user-selected export | Independent verification of the report or original execution timestamps |
| Demo | Synthetic examples of actions, failures and recovery | Any real agent activity |

The first CPU/rate sample is a warm-up, not zero usage. Access failures, exhausted scan bounds, and missing counters are reported as unavailable or unknown rather than silently converted into successful observations.

## Activity state

[`StateEngine`](../apm/core/state.py) consumes canonical events and retains the most recent supported summary. Its records are labelled `inferred` with interpretation level `inference` and source event IDs. It does not reconstruct plans, goals, or thoughts.

| State | Typical supporting evidence |
| --- | --- |
| `IDLE` | Initial state or session stop |
| `OBSERVING` | Session start, ordinary process first observation, workspace change with actor unverified, or a completed process with no remaining active entry |
| `EXECUTING` | A reported command/process `START` or `EXECUTE` without a recognized test runner |
| `TESTING` | A recognized test command or a test start event |
| `VERIFYING` | A verification-category event |
| `ERROR` | An error-category event, reported `FAIL`, or nonzero command exit code |
| `UNKNOWN` | An unavailable observation |

These are current summaries, not an exhaustive workflow model. The engine tracks active command/process entries and can return to another active entry after a stop. An ordinary `OPEN` establishes observation rather than execution unless its supported command identifies a test runner. Filesystem changes produce an actor-unverified summary. System samples and Git snapshots do not replace the current activity state.

Synthetic source events add `[DEMO / SYNTHETIC]` to the derived summary. The derived record remains an inference; the source event retains its synthetic status. Replay adds a **Recorded** context and computes the same rules from the replayed sequence.

## Test recognition and wrapper limits

Recognition is intentionally narrow: direct `pytest`, `py.test`, `ctest`, `python -m pytest`, `python -m unittest`, `npm test`, `npm run test`, `cargo test`, and `dotnet test` forms can be recognized. It does not interpret arbitrary shell wrappers, embedded `python -c` code, or text merely mentioning a test command. Argument forms outside the implemented rule, such as extra Python flags before `-m`, need not be recognized.

The attach observer collects less command information than an explicit imported report can contain. It omits the root process arguments and retains only selected descendant tool prefixes; most arbitrary arguments are never emitted. As a result, every runner recognized by the state engine is not necessarily observable through attach mode.

The live interpreter can produce inferred test start or pass/fail events from a recognized command and a reported exit code. Attach mode does not obtain process exit codes, and a zero exit code is not an assertion count. The CLI import path does not run this live test interpreter. Demo test counts are synthetic fixtures.

## Four semantic magnifications

The actual GUI labels are **Overview**, **Activity**, **Evidence**, and **Raw event**. They show different amounts of detail from one already-redacted selected event; changing lenses does not invoke a model or create a new inference.

| GUI label | Content | Relationship to the conceptual vocabulary |
| --- | --- | --- |
| Overview | Action, target, status explanation, confidence and interpretation level | Closest to the Human view |
| Activity | Structured action, category, source, agent, time and certainty fields | Closest to the Action view |
| Evidence | Target, event/session IDs, reference and redacted metadata | Supplies Engineering detail and Evidence provenance |
| Raw event | Redacted canonical JSON | Supplies the complete retained event representation for Evidence/Engineering inspection |

Human, Action, Engineering, and Evidence describe the intended progression of semantic detail. They are not alternate button names or a perfect one-to-one renaming of the shipped lenses. In particular, the existing **Evidence** pane serves both provenance and engineering inspection.

## Display controls

**Pause display** freezes the visible rows while observation and recording continue. **Clear view** removes retained presentation rows without deleting recording files. Category/status filters and search operate on retained rows; they cannot recover rows already evicted from the bounded view. Search covers the displayed event identity/action fields, not arbitrary nested metadata.

The activity panel is a current inferred summary, not simply the most recent timeline action. **OBSERVATION ACTIVE**, **DEMO SYNTHETIC**, and **REPLAY PASSIVE** distinguish live, synthetic, and recorded contexts. A stopped display or an unavailable signal must not be read as proof that the observed agent stopped working.
