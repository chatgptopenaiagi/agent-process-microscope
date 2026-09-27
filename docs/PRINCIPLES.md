# The twelve APM principles

These principles guide design and review. They describe project intent and engineering
requirements, not additional license terms. APM is experimental; claims of compliance
must remain tied to implementation and validation evidence.

## 1. Evidence before interpretation

Every displayed conclusion should lead back to retained evidence, its source and
its limits. A useful narrative does not justify inventing facts.

## 2. Observation before attribution

A changed file does not automatically mean Codex changed it. Process ancestry,
workspace proximity and timing can be clues; none alone establishes the actor.

## 3. Unknown is valid

Use UNKNOWN when a fact cannot be established and UNAVAILABLE when a source cannot
supply it. An absent measurement is not zero, success or proof of inactivity.

## 4. Replay is not re-execution

Replay reconstructs recorded activity for inspection. It must never execute stored
commands, repeat browser actions or apply historical changes.

## 5. Stopping the microscope must not kill the specimen

Stopping attached observation is separate from terminating the observed process.
The observer may stop its own bounded helpers, but must leave attached work alone.

## 6. Synthetic means synthetic

Demo and fixture events remain explicitly labeled. Synthetic activity must not be
mixed into evidence of real observation or presented as a validation of real actions.

## 7. Secrets should be redacted before persistence

Minimize collection first, then redact before queues, presentation and durable
storage. Pattern redaction is best effort; it cannot identify every possible secret.

## 8. Observability must not become spyware

APM is not intended for keylogging, credential harvesting, covert surveillance or
hidden employee monitoring. Observation should be visible and understandable to
the person using the microscope. It is not an indiscriminate filesystem monitor.

## 9. Scope observation

Observe the selected process tree, session and workspace. Collect only what that
scope needs. Whole-machine telemetry must be labeled as aggregate, not agent usage.

## 10. Minimize observer effect

Use controlled polling, bounded queues, filtering and batched display updates.
Report gaps and drops instead of allowing the observer to overwhelm the specimen.

## 11. Evidence and derived meaning remain distinguishable

The human must be able to ask “How do we know?” Original unrestricted sensitive
streams need not be retained to answer that question. Genesis retains sanitized
observation metadata separately from explicitly derived events and states.

## 12. Codex is the first specimen, not the architecture

Agent-specific knowledge belongs in adapters. The canonical event model, state
engine, recorder, replay and GUI should remain useful for other agents and future
supported application instrumentation.

See [observability](OBSERVABILITY_MODEL.md), [security](../SECURITY.md), and
[implemented versus planned adapters](ADAPTER_MODEL.md).
