# Genesis status

Genesis is a working local observation foundation, version `0.1.0`. The implemented runtime was validated on Windows with 66 passing tests, a native synthetic-demo/passive-replay check, and a small owned process/workspace fixture. Publication documents that baseline; it does not silently add unimplemented adapters or rerun another agent's work.

## Implemented

| Capability | Status and boundary |
| --- | --- |
| Native desktop interface | Tkinter/ttk window with explicit live/demo/replay labels |
| Process attachment | Selected PID and verified descendants; sampled metadata, no workload termination |
| Workspace observation | Bounded metadata polling, exclusions, actor unverified |
| Git observation | Bounded read-only status and line-count metadata through hidden Windows helpers |
| System telemetry | Whole-machine CPU/RAM/disk/network; attribution unknown |
| Canonical events | Schema 1.0 validation, provenance, redaction and evidence references |
| Activity reconstruction | Conservative evidence-linked state inference |
| Local recording | Event/state JSONL plus lifecycle metadata and checkpoints |
| Passive replay | Bounded canonical input, chronological playback, fresh state reconstruction |
| Synthetic demonstration | Clearly labelled finite example sequence |
| Codex JSONL import | Explicit selected export, allowlisted reports, import-time provenance |
| Packaging | Python wheel and local windowed Python launcher; no standalone executable |

The shipped event lenses are **Overview**, **Activity**, **Evidence**, and **Raw event**. The conceptual Human/Action/Engineering/Evidence progression is explained in [Observability model](OBSERVABILITY_MODEL.md); it is not a claim that the GUI buttons have those conceptual names.

## Deferred or unavailable

| Capability | Genesis position |
| --- | --- |
| Managed launch of agents | Deferred; attach mode observes an already running process |
| Private reasoning or chain-of-thought capture | Outside the observation model |
| File contents and file-read tracing | Not collected by workspace polling |
| Browser/Joomla observation | Deferred |
| GPU telemetry | Unavailable; no probe configured |
| Existing private Codex session discovery | Not implemented; explicit exports only |
| Live Codex transport or model calls | Not implemented |
| General shell-wrapper interpretation | Not implemented |
| Standalone EXE, signed installer, auto-update | Deferred |
| WSL, remote or cloud observation | Not validated or implemented as dedicated transports |
| Guaranteed complete event capture | Not claimed; polling, bounds and overload can omit evidence |
| Tamper-proof or encrypted recordings | Not implemented |

## Validation and publication boundary

[Validation](VALIDATION.md) records the exercised environment and exact historical results. Windows/Python 3.14.7/Tk 9/psutil 7.2.2 is the tested baseline; packaging's broader version declarations do not imply equivalent testing elsewhere.

Source, tests, and curated documentation are suitable publication inputs. Runtime environments, private session recordings, caches, raw protocol exports, local logs and machine-specific shortcuts are not required to understand or build the project and should remain outside normal source publication.

The project is licensed under Apache License 2.0; see [LICENSE](../LICENSE) and [NOTICE](../NOTICE). Repository visibility, commits, tags, and release assets are publication operations, not runtime capabilities. This document does not assert that any particular remote, release, or public deployment exists.

Genesis completeness means the documented foundation works within these boundaries. It does not mean every item in the longer-term vision has been implemented.
