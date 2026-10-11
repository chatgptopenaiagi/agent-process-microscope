# ADR 0002: interpretations append to a separate journal

Status: implemented locally; acceptance results are tracked in
[engineering progress](../ENGINEERING_PROGRESS.md).

Keep the existing observation database, capsule schema and viewers unchanged.
Holmes uses a separate SQLite application ID and schema version 1. Full hypothesis
snapshots append as revisions: CREATE, REVISE, REVIEW, CORRECT, CHALLENGE and
VERIFICATION, plus versioned PATTERN declarations. Corrections never UPDATE earlier entries. An expected revision
prevents lost updates; request UUIDs make exact retries idempotent and reject a
different request using the same UUID. SQL transactions either commit a revision
or leave the previous history intact. Exclusive new-file backup uses SQLite's
online backup API; reopen validates the chain and revision/index consistency.

Each support/contradiction citation binds a whole-file capsule SHA-256, session
UUID and event UUID. Missing material belongs in an explicit missing-evidence
field, never in a silently accepted dangling citation. Reopening a journal does
not search the workstation for evidence: users explicitly reselect capsules.
History remains readable when a capsule is unavailable; challenges say so.

Unkeyed journal hashes detect accidental changes and support external tip pinning;
they do not authenticate reviewers or resist an attacker who rewrites all hashes.
SQLite triggers prevent accidental UPDATE/DELETE, not access by the file owner.
Human review is an interpretation only. There is no tool execution, permission
grant, network provider or credential interface in this module.

Producer declarations distinguish HUMAN_RECORDED, AGENT_REPORTED and SYNTHETIC.
Synthetic review fixtures cannot activate patterns matching real evidence classes.
No file-based declaration proves a person's identity. Report verification and
history reads share a transaction, so concurrent appends do not invalidate the
reported chain tip's scope.

Prefer bounded, deterministic checks to a model dependency. The skeptical report
resolves references, scans the selected capsules for explicitly conflicting report
outcomes, counts omitted/uncited material and explains unknown clocks and identity.
A lexical causal-word flag is explicitly a heuristic, not semantic understanding.
No automatic rule proves a hypothesis true. Human-supported states retain limits.

Bounds: eight capsules (4 MiB each), 40 references per evidentiary role, 20 text
items per hypothesis list, 2,000 journal entries, 64 KiB per entry, 100-entry pages.
SQL operations run in a single GUI worker; Tk owns only presentation. Reports use
escaped text, generated internal links, no external assets, and exclusive output
creation. Existing Genesis/observatory storage and replay are not migrated.
