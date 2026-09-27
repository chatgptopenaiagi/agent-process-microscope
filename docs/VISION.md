# Vision: a microscope with a timeline

An AI agent can perform many externally visible actions while its interface says
only that it is working. APM aims to make those actions inspectable as they happen
and understandable afterward, without claiming access to the agent's private mind.

The microscope supplies adjustable detail: a short human explanation, an action,
engineering facts and the underlying sanitized evidence. The television supplies
continuity: related activity unfolds on a live timeline and can later be replayed.
Engineering observability supplies the discipline: every claim has a source, scope,
time and uncertainty.

The intended human questions are:

- What observable activity is happening now?
- Which evidence supports the description?
- Which facts are inferred, missing or unavailable?
- What changed before an error, and what observable action followed it?

Genesis implements a small Windows foundation: attach observation, workspace/Git
metadata, machine telemetry, a supported Codex export importer, canonical events,
conservative states, a native GUI and passive replay. It does not reconstruct a
complete agent workflow or prove universal attribution.

Future adapters may cover WSL, browsers, applications, cloud agents, development,
testing, CAD and simulation. Those are possible sources, not current capabilities.
Each must explain what it can observe and how its evidence relates to other sources.

## Joomla as a future example

A supported browser/application integration might eventually show:

```text
Agent opens Joomla Administrator
  → opens Components
  → opens configuration
  → changes a field
  → presses Save
  → Joomla returns a response
  → an instrumented check verifies the observable result
```

Each step would need evidence: a navigation notification, tool action, target
identifier, response or verification result. A click would not prove a save succeeded;
an HTTP response would not necessarily prove the intended application state.

The user should see both **what happened** and **how we know**. Joomla is a future
demonstration, not the definition of APM. Genesis contains no Joomla or browser
instrumentation and performs no administrator actions.

[Principles](PRINCIPLES.md) · [Semantic Television](SEMANTIC_TELEVISION.md) · [Roadmap](../ROADMAP.md)
