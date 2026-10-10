# AEGIS comparative investigation — 10 October 2026

Pinned source: [bfc03c45bb2b5b253448b0d33cb305259bec0e90](https://github.com/antropos17/Aegis/commit/bfc03c45bb2b5b253448b0d33cb305259bec0e90),
resolved through the GitHub connector. This is a source inspection, not a native
AEGIS execution, security audit or benchmark. No AEGIS code/assets were reused.

The public web view of `master` returned inconsistent cached ages, including old
unbounded-buffer code. Direct shell GitHub access was blocked by this execution
environment's proxy. The connector then retrieved commit-pinned source; findings
below use that source and supersede the stale web observations.

| Area | AEGIS evidence inspected at the pinned commit | APM interpretation and actual state |
|---|---|---|
| Architecture/UI | `package.json`, `docs/README.md`: Electron/Svelte application, separate native sidecar/build/test surfaces | Keep Tk/psutil; no evidence that migrating GUI stacks helps the first investigation |
| Detection/identity | `src/main/process-scanner.js`, `process-identity.js`: population reliability, OS birth-time identity, explicit unknown identity | Genesis already has scoped PID/create-time tracking; retained unchanged. APM does not add whole-machine signature discovery |
| Files/sensitive paths | `src/main/file-watcher.js`, `attribution.js`: watcher/handle health, coverage transitions, path heuristics labelled inferred | Retain APM workspace metadata only; no sensitive-directory census, file contents or inferred authorship |
| Network | `src/main/network-monitor.js`: endpoint collection, scope health and DNS evidence; missing DNS does not itself establish wrongdoing | APM still has machine aggregate rates only. Per-process endpoints deferred; no TLS inspection |
| Audit durability | `src/main/audit-logger.js`: bounded buffer, persisted/pending/dropped distinction, loss markers, history health | APM durable outbox stops at capacity and retains a loss marker; no claim that a valid chain proves completeness |
| Audit integrity | `src/main/audit-hashchain.js`: SHA-256 chains within daily files, documented valid-prefix/truncation limits | Independently implemented SQL receipt chain with domain separation and optional externally held tip; sequence gaps separate from chain integrity |
| Historical queries | `src/main/audit-index.js`: rebuildable SQLite WAL projection over canonical JSONL; index failure must not redefine canon | APM SQL is canonical for the new memory. Legacy JSONL remains independently readable. Explicitly different failure/transaction model |
| Investigation | `src/main/ai-analysis.js`: Anthropic API analysis and bounded/sanitized provider handling | No provider enabled in APM. Local deterministic failure explanation cites event IDs and persists its checkpoint |
| Decisions/action controls | `docs/ALERTS-AND-PERMISSIONS.md`: saved review decisions and separate manual process actions | APM records opinions only. No action API, approval inheritance or process termination surface |
| Agent interoperability | `process-scanner.js` uses a signature database; current docs describe optional MCP setup | APM's generic reporter/read-only protocol works independently of Codex. An MCP server and multi-agent coordinator remain unimplemented |
| Tests/performance | `package.json` names Vitest, frontend/Electron checks and benchmark scripts | AEGIS tests were not run. No coverage %, resource figure or comparative speed claim is adopted |

AEGIS contributes useful comparative lessons: qualify sensor failure, preserve
identity uncertainty, distinguish pending from durable records, and separate review
from control. These also match APM's pre-existing principles and the owner's mission;
they are established engineering practices, not claims of invention by either project.

The fetched files carry MIT headers where inspected; the repository
[LICENSE](https://github.com/antropos17/Aegis/blob/bfc03c45bb2b5b253448b0d33cb305259bec0e90/LICENSE)
names AEGIS Contributors. MIT reuse would require its notice and permission text.
`package.json` also lists a vendor icon license in packaged files. We have not
audited every dependency or asset license and make no blanket reuse conclusion.
No source, branding, assets, rule databases or packaged components were copied.
See the [attribution register](AEGIS-ATTRIBUTION-REGISTER.md) for exact sources.
