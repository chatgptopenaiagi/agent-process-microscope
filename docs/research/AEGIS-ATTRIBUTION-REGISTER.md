# AEGIS attribution register

Source commit for every entry: **bfc03c45bb2b5b253448b0d33cb305259bec0e90**.
Inspected 10 October 2026 through the GitHub connector. Descriptions below are
paraphrases. Every APM implementation is independently written. **Source-code
reuse: none.** No AEGIS visual assets, branding or third-party packages were copied.

| Concept and exact source | Original description / APM interpretation and difference | Verification |
|---|---|---|
| [Bounded durable history](https://github.com/antropos17/Aegis/blob/bfc03c45bb2b5b253448b0d33cb305259bec0e90/src/main/audit-logger.js) | AEGIS buffers JSONL and distinguishes pending/persisted/dropped records. APM uses a durable SQLite outbox, atomic ack-after-commit batches and overflow-stop markers rather than drop-oldest buffering | APM disconnect, ack-loss, capacity-marker and restart tests; AEGIS source inspection only |
| [Hash chains](https://github.com/antropos17/Aegis/blob/bfc03c45bb2b5b253448b0d33cb305259bec0e90/src/main/audit-hashchain.js) | Daily file chains detect some modifications, not missing tails. APM chains SQL receipts using a different canonical profile/domain prefix, with externally supplied tip comparison | APM tamper/index/expected-tip tests; no imported hash implementation |
| [SQLite history](https://github.com/antropos17/Aegis/blob/bfc03c45bb2b5b253448b0d33cb305259bec0e90/src/main/audit-index.js) | AEGIS's SQL is a disposable index of JSONL. APM's new SQL ledger is durable canon, alongside preserved Genesis JSONL | APM recovery, concurrent access, backup and atomic rollback tests; different schema |
| [Explicit attribution](https://github.com/antropos17/Aegis/blob/bfc03c45bb2b5b253448b0d33cb305259bec0e90/src/main/attribution.js) | Discrete evidence-backed/inferred/unattributed relationships. APM keeps its existing evidence model and adds receiver-owned AGENT_REPORTED classification | APM role/provenance tests; no AEGIS evidence vocabulary or scoring copied |
| [Generation identity](https://github.com/antropos17/Aegis/blob/bfc03c45bb2b5b253448b0d33cb305259bec0e90/src/main/process-identity.js) | PID plus OS birth time; unavailable identity remains explicit. APM already used PID/create-time before this mission | Existing Genesis observer tests retained; no new observer implementation credited to AEGIS |
| [Sensor coverage](https://github.com/antropos17/Aegis/blob/bfc03c45bb2b5b253448b0d33cb305259bec0e90/src/main/file-watcher.js) | Coverage and failure are independent of an empty event list. APM carries unknown/unavailable records and source-loss markers into investigations | APM malformed-source/gap/native-workload evidence; no handle scanning adopted |
| [Network uncertainty](https://github.com/antropos17/Aegis/blob/bfc03c45bb2b5b253448b0d33cb305259bec0e90/src/main/network-monitor.js) | Scope and DNS evidence qualify endpoint interpretation. APM defers endpoint attribution | Research only, no implementation or native network validation |
| [Investigation boundary](https://github.com/antropos17/Aegis/blob/bfc03c45bb2b5b253448b0d33cb305259bec0e90/src/main/ai-analysis.js) | Provider-assisted activity analysis. APM chooses provider-free rules and per-event citations first | APM native failure investigation and Tk tests; no provider code reused |
| [Review versus control](https://github.com/antropos17/Aegis/blob/bfc03c45bb2b5b253448b0d33cb305259bec0e90/docs/ALERTS-AND-PERMISSIONS.md) | Review decisions differ from separate manual process actions. APM has no operational action interface | Decision-reference and forbidden-operation tests |

License obligations: inspected code headers and the pinned root LICENSE say MIT;
reuse of substantial source portions would require the copyright and permission
notice. Since no code/assets were reused, no third-party code notice was added
to APM's Apache-2.0 sources. File-level and third-party restrictions outside these
inspected files remain unreviewed. This register documents conceptual comparison,
not an assertion that AEGIS's entire distribution has one unrestricted license.
