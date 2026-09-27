# Semantic Television

A screen recording stores a sequence of pixels. It can show a display but does not
by itself establish which process caused an action, whether a command completed,
or whether the visible application state was saved.

APM instead attempts to present evidence-backed events over time:

```text
PROCESS FIRST OBSERVED
  → WORKSPACE METADATA CHANGED
  → DIRECT TEST RUNNER RECOGNIZED
  → COMMAND EXIT REPORTED BY AN INSTRUMENTED SOURCE
  → CONSERVATIVE STATE UPDATED
```

This is an illustrative combination of evidence sources, not a claim that live
attach supplies all these facts. Genesis attach cannot recover a process exit
code; an imported Codex command report may supply one. The import's timestamps
are observation/import times, not reconstructed historical execution times.

With stronger instrumentation, a future presentation might support:

```text
EDIT → TEST → FAIL → CORRECT → TEST → PASS → VERIFY
```

The words must be earned. A metadata change does not prove an edit by the agent.
A second edit does not prove a correction. A zero command exit does not prove
that every intended test ran. Verification needs its own observable result.

## Presenting meaning without manufacturing certainty

Genesis links events to source metadata and derived states to event IDs. The GUI
offers four lenses over the same event and preserves OBSERVED, INFERRED, SYNTHETIC,
UNKNOWN and UNAVAILABLE distinctions. Its short state summaries are intentionally
conservative. A confidence annotation is not a substitute for provenance.

In the current UI, replay uses the same state engine over recorded events. It does
not repeat actions, read private reasoning or generate a new account of inaccessible
events. Gaps and omitted evidence remain gaps. The complete sanitized canonical
event can be inspected even when its narrative interpretation is weak.

Longer-session summaries, richer causal links, coordinated application events and
evidence graphs remain research directions. See [the roadmap](../ROADMAP.md).
