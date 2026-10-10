# Capability roadmap

The [Observatory development slice](docs/OBSERVATORY.md) now implements local SQL
memory, optional independent receiver/companion processes, scoped investigation
queries and native Memory / Ask. See [current measured evidence and next step](docs/ENGINEERING_PROGRESS.md).
One owner-run protected Codex engineering slice is now verified against retained
evidence. The broader observatory mission and bidirectional dialogue remain incomplete.

These phases describe possible capabilities, not deadlines or commitments. Only
Genesis 0.1 below and the linked development slices are implemented. Holmes now
has a guided native workflow and locally tested portable/wheel development builds;
see [desktop qualification](docs/DESKTOP_CHECKPOINTS.md). The next gate is a clean
ordinary-user Windows x64 portable qualification, followed by binary-license and
installer lifecycle gates. Later work must preserve the [twelve principles](docs/PRINCIPLES.md).

## Genesis 0.1 — implemented experimental foundation

- Native Windows GUI and Attach mode.
- Scoped process and filesystem metadata observation; read-only Git summaries.
- Aggregate system telemetry, canonical events and bounded in-process dispatch.
- Conservative state reconstruction, timeline, filters/search and four evidence views.
- Durable session recording and passive replay.
- Explicit synthetic demo, allowlisted Codex JSONL import and best-effort redaction.

The [Genesis status](docs/GENESIS_STATUS.md) and [validation](docs/VALIDATION.md)
describe exact limits. No production security or cross-platform certification is claimed.

## Phase 2 — stronger agent correlation, planned

Potential work includes managed Codex launch, richer parent/child correlation,
stronger command evidence, improved reconstruction, richer Git visualization,
session summaries, timeline improvements and profiling on larger repositories.
Managed launch needs explicit process ownership, output handling, cancellation
and permission semantics. It must not blur Stop observation with Stop agent.

## Phase 3 — application observation, planned

Potential work includes supported browser instrumentation, semantic browser events,
a Joomla Administrator demonstration, CLICK/TYPE/NAVIGATE events, server-response
correlation and application-state verification.

```text
CODEX → BROWSER → JOOMLA ADMINISTRATOR → COMPONENTS
      → CONFIGURATION → CHANGE → SAVE → RESPONSE → VERIFY
```

This is a conceptual future sequence. Each step needs supported tool/application
evidence; a screen image or click alone cannot establish application success.
[Joomla use case](docs/VISION.md#joomla-as-a-future-example).

## Phase 4 — cross-environment observation, planned

Potential work includes WSL and Linux adapters, multiple simultaneous agents,
cross-agent timelines, richer replay and session comparison. Shared event structure
does not by itself solve clock alignment, identity, transport or trust boundaries.

## Research horizon — exploratory

Cloud-agent observation, evidence graphs, distributed observability, workflow
visualization, long-session semantic compression, standardized agent-observability
protocols and external integrations need investigation before implementation claims.

Private reasoning inspection, covert monitoring and unrestricted credential capture
are outside the project's purpose, not future capability milestones.
# Cognitive observatory follow-up

The native full-session qualification review is implemented and tested locally.
Capsules v1 now add offline selected-session export, independent content checks,
isolated read-only review, preserved citations and deterministic two-session
comparison. Imported provenance remains unverified; comparisons do not establish
causation. See [measured results](docs/ENGINEERING_PROGRESS.md).

Holmes now persists cited hypotheses, append-only review/correction history and
explicit insufficient-evidence challenges separately from observations. A bounded
versioned pattern subset and offline synthetic assessment protocol are implemented.
Next: add a native pattern promotion/validation workflow with labeled validation
records, explicit counterexamples and reviewable false-match results. Pattern
management currently requires the Python API. Real provider cooperation, forensic
adapters and paired federation remain later gates.
Distribution still requires per-user storage defaults, isolated builds and clean-
machine acceptance. No remote publication or release is authorized.

See [component boundaries and phased gates](docs/COGNITIVE_ARCHITECTURE.md) and
[the capsule architecture decision](docs/decisions/0001-capsules.md).
