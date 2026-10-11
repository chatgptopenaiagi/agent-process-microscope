# Holmes Lab: evidence-grounded interpretations

Holmes adds a separate, local SQLite investigation journal. It does not change
observations, capsules, Codex, authentication or provider configuration. It has
no execution capability. A human assessment is an opinion about evidence, not
authorization to run a command. This is experimental software, not certified
forensic tooling. See [architecture decision](decisions/0002-holmes-journal.md).

## Start an investigation

```powershell
.\.venv\Scripts\python.exe -m apm holmes gui
# Reopen a selected journal:
.\.venv\Scripts\python.exe -m apm holmes gui .\reports\my-investigation.sqlite3
```

APM opens Holmes Lab by default. Advanced tools opens the original microscope;
observation, replay, Memory/Ask, qualification review and capsule review remain available.

1. Choose **Create a case** and a new `.sqlite3` destination, or **Open an existing case**.
   Do not select an observation database: it has a different format and is rejected.
2. Choose **Open evidence capsule** for each explicitly selected evidence source. Import
   verifies its structure and internal checksums. This does not authenticate its
   producer. Nothing is copied into the source database or capsule.
3. On **Evidence**, browse 100-record pages. Select a record and choose
   **Use as support** or **Use as contradiction**. Source classes are exporter
   declarations; synthetic events remain synthetic.
4. On **Explanation**, enter the case title, purpose, declared reviewer, explanation,
   uncertainty, alternatives, missing evidence and proposed checks. Choose
   **Save new explanation**. Multiple explanations can share a case.
5. Select a saved hypothesis. **Inspect saved citation** opens its underlying
   record. The advanced tab exposes the complete structured record when needed.
6. **Challenge selected explanation** checks citations, conflicting final reports, omissions,
   source classes and knowledge limits. It never runs the proposed checks.
7. Choose a review state, enter a reason and **Record assessment**. Use
   **Correct earlier assessment** to append a correction. **Revise selected**
   appends changed claim/evidence and returns its review state to PROPOSED.
8. **History** shows the entire journal through 100-entry pages. Select
   any revision for its explanation and advanced structure. No earlier assessment
   is erased. REJECTED and SUPERSEDED are review states, not deletion operations.
9. **Export report…** writes a new HTML or JSON file for the selected case. Existing
   files are never overwritten. Review any report before sharing: user-entered
   descriptions, identifiers and timestamps can still be sensitive.
10. Close and reopen the journal later, and explicitly reopen the source capsules.
    The journal does not search the workstation. Unavailable citations remain
    visible in history and reports; challenges cannot silently treat them as verified.

The journal and source evidence are plaintext under existing filesystem controls.
No global permissions change, encryption or reviewer authentication is supplied.
Use **Backup…** for a new SQLite online backup. Recovery reopens committed history
after interruption; it does not attempt to repair corrupt data. Keep an external
tip/hash if protection against a wholly replaced journal is needed.

## Public Python contract

`apm.holmes.model.Catalog` opens up to eight capsules. A reference contains exactly
`capsule_sha256`, `session_id`, `evidence_id`. Resolution checks all three. Event
IDs from another capsule/session cannot satisfy it. Unresolvable material belongs
in `missing: [{reference: <reference or null>, reason: <text>}]`.

`Journal.create(new_path)` exclusively creates schema 1; `Journal(path)` opens
only that format and verifies it. `propose(...)` accepts claim, support, contradict,
alternatives, missing, checks and uncertainty. Each call requires a UUID request ID.
An exact retry returns the original revision; changing a request under its old ID
is rejected. `revise(id, expected_revision, producer, kind, detail, catalog,
request_id=...)` rejects stale edits. Public kinds are:

| Kind | Detail and effect |
|---|---|
| REVISE | `hypothesis`, `reason`; new snapshot, state PROPOSED |
| REVIEW / CORRECT | `state`, `reason`; interpretation only; correction requires a prior review |
| CHALLENGE | Empty detail; deterministic report appended with algorithm version |
| VERIFICATION | `procedure`, `outcome`, `limitations`, `references`; outcome REPORTED_PASS, REPORTED_FAIL or UNAVAILABLE, never an executed test |
| PATTERN | Versioned pattern definition described below; no automatic promotion |

Review states: PROPOSED, UNDER_REVIEW, SUPPORTED_WITH_LIMITATIONS, CONTRADICTED,
INSUFFICIENT_EVIDENCE, REJECTED, SUPERSEDED. There is no unrestricted VERIFIED state.
`producer_class` defaults to HUMAN_RECORDED for local UI input; AGENT_REPORTED may
propose interpretations but cannot submit human reviews. Automated demonstrations
explicitly use SYNTHETIC. These declarations are not an authentication mechanism.
Challenges are classified INFERRED and retain the producer declaration separately.

`history(id=None, after=0, limit=100)`, `latest(id)`, `verify(expected_tip=None)`,
`backup(new_path)` and `snapshot()` expose inspectable history and scoped checks.
Report generation verifies and reads history in one consistent SQLite snapshot.
An unkeyed SHA-256 chain covers canonical entry bodies and index/revision checks;
the previous hash is domain-separated with `APM-Holmes-journal-v1\0`.
No existing observation schema is migrated. No earlier local/public capsule schema
changes. Unsupported journal versions fail closed.

Bounds: eight 4-MiB capsules, 40 references per role, 20 list entries, 2,000 journal
revisions, 64 KiB per revision, 100-row pages, 160-MiB input database and a 10-second
verification deadline. SQL lock waits are bounded at three seconds. One worker
serializes GUI file/SQL jobs; repeated clicks do not grow a work queue. Closing
discards pending presentation updates and lets a bounded active transaction finish.

## Skepticism, reports and uncertainty

The challenge resolves selected citations and scans their capsules for incompatible
final exit reports for the same declared stream/turn/item. It records uncited and
exporter-omitted counts, explicit contradictions, synthetic/reported classes,
unknown clocks, unverified identities and alternatives. It does not decide whether
a cited fact semantically proves a claim. Causal wording detection is a disclosed
English lexical heuristic, with false negatives possible. Every automated conclusion
remains INSUFFICIENT_EVIDENCE for truth or a unique cause.

HTML escapes imported text, uses generated internal citation links and a restrictive
content security policy. It contains no scripts, external resources or executable
links. Reports include cited metadata and the complete interpretation history,
not full raw sessions or original databases. They are limited to 32 MiB of output;
an interrupted export can leave a partial file, which must not be treated as complete.
JSON retains missing references and scoped checks for independent review.

```powershell
.\.venv\Scripts\python.exe -m apm holmes verify .\reports\my-investigation.sqlite3
.\.venv\Scripts\python.exe -m apm holmes report .\reports\my-investigation.sqlite3 --case CASE_UUID --capsule .\reports\selected.apmcapsule --output .\reports\new-case.html
```

## First semantic-memory subset

Patterns append as PATTERN revisions of their source hypothesis. The API accepts
`pattern_id`, `version`, `source_review_revision`, `description`, `required`,
`optional`, `counterexamples`, `review_note`, and `disposition` (ACTIVE or RETIRED).
The source revision must be a supporting review with resolvable evidence and at
least one matching supporting example. Synthetic review fixtures can only promote
patterns whose required class is SYNTHETIC. New versions must increase by one.
Retirement remains possible when source capsules are unavailable.

Matching is exact and explainable. Allowed criteria are source, category, action,
evidence_class, comparison_key and exit_code. Required criteria must include source,
category, class and at least one additional attribute; missing required attributes
never match. Optional differences are retained. Counterexamples exclude matches.
At most 100 patterns scan at most 8,000 retained records; each result retains 20
cited examples with total/truncation counts. A later claim revision or adverse
human correction suspends use of the earlier pattern until reassessed.

**Find reviewed patterns** displays results in the lab. Pattern creation and version
management currently use the Python API; a native promotion/validation editor is
not yet implemented. History records promotions, review provenance and retirement,
but there is no general pattern-specific validation registry or calibrated retrieval
benchmark. Tests deliberately measure a tiny labeled fixture, not production quality.

```powershell
.\.venv\Scripts\python.exe -m apm holmes patterns .\reports\my-investigation.sqlite3 --capsule .\reports\selected.apmcapsule
```

## Offline cooperation boundary

`apm.holmes.cooperation` implements `apm-assessment-v1`: message UUID, declared role/
producer/model version, timestamp, capsule/session scope, hypothesis and byte/time/
token bounds. Batches of at most eight assessments validate every support/contrary
citation and reject out-of-scope or duplicate messages. HUMAN_REVIEWER is a declared
role, not verified identity. AI agreement never proves a claim.

The demonstration is two synthetic local assessments and deterministic verification,
not two real model agents or authenticated live communication. Time/token fields
are contracts only: no provider runtime, billing, transport or metering exists.
No messages grant execution authority or automatically become journal reviews.

## Reproduce acceptance

```powershell
.\.venv\Scripts\python.exe scripts\holmes_demo.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_holmes.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\run_sandbox_checks.py
```

The fresh-process demo creates two synthetic capsules, a hypothesis with opposing
citations, challenge, review, correction, reopen, backup, reports and synthetic
cooperation responses. Its parent independently recomputes the journal chain and
checks source database/capsule hashes. All artifacts use a new ignored reports
directory. The original owner qualification is neither rerun nor exported.

Automated Tk interactions are distinct from visible human acceptance. The current
environment's restricted temporary-directory behavior and both suite results are
recorded separately in [engineering progress](ENGINEERING_PROGRESS.md). No standard
failure is hidden by a compatibility pass.
