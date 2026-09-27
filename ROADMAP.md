# Capability roadmap

These phases describe possible capabilities, not deadlines or commitments. Only
Genesis 0.1 below is implemented. Later work must preserve the [twelve principles](docs/PRINCIPLES.md).

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
