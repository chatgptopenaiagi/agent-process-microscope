# Glossary

| Term | Meaning in Agent Process Microscope |
| --- | --- |
| Adapter | A scoped source reader that returns payloads for normalization. |
| Agent | The selected external workload or labelled source being observed; APM does not assume access to its internal state. |
| Attach | Observe an already running root PID and verified descendants without owning their lifecycle. |
| Canonical event | A validated schema 1.0 event carrying identity, action, evidence status, provenance and redacted metadata. |
| Confidence | An implementation-supplied 0–1 indicator, not a calibrated probability or proof of attribution. |
| Controller | Owner of one live/demo collection session, its worker, queues, state engine and recorder. |
| Derived state | An evidence-linked inference such as `TESTING` or `OBSERVING`, separate from its source event. |
| Dropped | In the UI, the combined event-bus and display-queue drop count; session metadata keeps these components separate. |
| Evidence | Retained external observations or reports and their provenance; not hidden reasoning. Also the name of one shipped UI lens. |
| Event bus | The bounded live delivery queue feeding recording, state inference and display. Explicit CLI import bypasses it. |
| Genesis | The validated initial local-observation foundation, not completion of all planned capabilities. |
| Human / Action / Engineering / Evidence | Conceptual levels of explanation. The actual lenses are Overview, Activity, Evidence and Raw event; their mapping is approximate. |
| Imported report | A claim read from an explicitly selected export, not independently verified OS evidence. |
| Inference | A labelled conclusion from available evidence, with references and limits. |
| Magnification / lens | One of four presentations of a selected, already-redacted event; it does not trigger additional observation or model reasoning. |
| Metadata-only observation | Collection of attributes such as timestamps, sizes, paths, status or resource counters without storing file contents. |
| Observation | A scoped adapter report about externally available evidence. It may still have unknown attribution or incomplete coverage. |
| Passive replay | Read and present recorded events while reconstructing state, without executing recorded actions or starting observers. |
| Pause display | Freeze visible live rows while observation and recording continue. This differs from pausing replay progression. |
| Provenance | The recorded source and basis of an event, including imported or synthetic origin. |
| Raw event | The UI lens containing redacted canonical JSON, not unredacted terminal output or original private source bytes. |
| Raw reference | A retained producer reference or sanitized-metadata digest. The field name does not imply that raw content is stored. |
| Recorder | Local writer of session metadata, canonical events and derived-state records. |
| Redaction | Best-effort exclusion or masking before normal display and persistence; not a guarantee that metadata is safe to publish. |
| Session | One recording with its own UUID, scope, lifecycle metadata and event stream. |
| State engine | Deterministic rules that turn qualifying events into conservative current-activity summaries. |
| Synthetic | Deliberately generated demo evidence, visibly distinct from live observation. |
| System aggregate | A whole-machine metric with unknown attribution to a selected agent. |
| Unknown | Evidence is insufficient to establish a stronger conclusion. |
| Unavailable | An observation could not be supplied; this is not proof of inactivity. |
| Workspace | The user-selected directory defining filesystem/Git observation scope, subject to exclusions and bounds. |

For operational detail, see [Event model](EVENT_MODEL.md), [Observability model](OBSERVABILITY_MODEL.md), [Replay model](REPLAY_MODEL.md), and [Adapter model](ADAPTER_MODEL.md).
