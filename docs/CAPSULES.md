# Evidence Capsules v1

APM can export one explicitly selected session to a local `.apmcapsule` file,
verify it without the source database or original model, open its evidence and
citations read-only, and compare it with a second session. No provider, network,
database migration or new runtime dependency is required.

This is an unsigned, bounded JSON exchange profile. It is not a forensic image,
authenticated collector record, legal custody system, BagIt implementation or
CASE-conformant document. See the [standards decision](decisions/0001-capsules.md).

## Safe first use

Generate two clearly synthetic sessions and capsules:

```powershell
.\.venv\Scripts\python.exe scripts\capsule_demo.py --records 120
```

The script creates a new ignored report directory, prints its aggregate result
location, verifies a capsule in a fresh process, checks citations and real
withdrawn Tk widgets, and compares the two sessions. It never launches Codex or
opens the retained owner qualification database. Generated files remain local.

For your own explicitly selected database, choose a case UUID and session UUID:

```powershell
.\.venv\Scripts\python.exe -m apm capsule export SELECTED.sqlite3 --session SESSION_UUID --case CASE_UUID --output NEW.apmcapsule
.\.venv\Scripts\python.exe -m apm capsule verify NEW.apmcapsule
.\.venv\Scripts\python.exe -m apm capsule inspect NEW.apmcapsule --after 0
.\.venv\Scripts\python.exe -m apm capsule inspect NEW.apmcapsule --evidence-id EVENT_UUID
.\.venv\Scripts\python.exe -m apm capsule gui NEW.apmcapsule
.\.venv\Scripts\python.exe -m apm capsule compare FIRST.apmcapsule SECOND.apmcapsule
```

**Open capsule…** in the ordinary GUI opens the same read-only native viewer.
Select a receipt and use **Open cited record** to resolve evidence on any page.
**Compare another session…** shows the comparison and its cited findings. Missing
references display UNKNOWN. Imported text is displayed as text, never interpreted
as instructions, HTML, scripts, permissions or executable commands.

Export requires a new destination and refuses overwrite. The default `minimal-v1`
profile replaces free-text targets with category/action, excludes human opinion
records, strips agent/principal identifiers, process identifiers, structured paths
and unlisted metadata, and maps unrecognized source labels to `other`. UUIDs,
timestamps, declared source classes, receipt fingerprints and selected outcome
metadata remain disclosed. These can still be sensitive.

`--include-human` explicitly includes opinion records. `--include-text` selects
`text-v1`, retaining sanitized free text, which can contain personal information
and paths. Human records still need their separate flag. Redaction is best effort,
not a declaration that the artifact is safe to publish. Review the manifest and
every selected disclosure before sharing. Export is not publication permission.

`--expected-tip` on export checks an independently retained source-database tip.
`--expected-sha256` on verify/inspect/gui checks an independently retained digest
of the entire capsule file. Neither value is a signing identity or secret.

## Contract and independent verification

The [JSON Schema](../schemas/evidence-capsule-v1.schema.json) documents the closed
structure. The [stdlib implementation](../apm/evidence/capsule.py) additionally
checks semantic consistency and digests; JSON Schema validation alone is not a
full verification. No external schema or referenced resource is fetched.

The root contains exactly `manifest`, `manifest_sha256` and `records`.
The manifest identifies format/version, case/session, export timestamp,
canonicalization/algorithm, record count, payload digest, exporter source claims,
disclosure policy, missing references and mandatory limitations. Source database
tip/counts and record fingerprints are declarations carried from export; the
recipient cannot reverify the original chain from redacted selected receipts.

Each record preserves its event UUID, original receipt number, stream/sequence,
sequence gap count, declared origin/class, normalized source, category/action,
status, event timestamp, receiver timestamp, time-basis label, source fingerprint,
target, allowlisted attributes and citation UUIDs. Source time and clock uncertainty
are explicitly null in v1. Receipt ordering is checked, not interpreted as causal
or cross-machine execution ordering. Unlisted original metadata and external
artifact contents are not included. Saved investigations retain citations,
algorithm, inspected/total counts, truncation and checkpoint metadata; their prose
is omitted under the minimal profile. Their original bounded scope is not
upgraded by export.

Canonical profile `apm-json-v1` uses sorted object keys, compact JSON separators,
ASCII escaping, no Unicode normalization, and no floating-point numbers. It is
not RFC 8785/JCS. An independent Python implementation needs only the standard
library for these content checks:

```python
import hashlib, json
def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=True, allow_nan=False).encode('ascii')
    return hashlib.sha256(raw).hexdigest()
assert digest(document['records']) == document['manifest']['records_sha256']
assert digest(document['manifest']) == document['manifest_sha256']
```

This excerpt demonstrates digest calculation on an already safely parsed document;
it is not the complete untrusted-input validator. The tests execute a separate
isolated interpreter using this independent calculation. A rewriter can recompute
both unkeyed digests. Only a separately trusted digest detects that replacement;
signer authenticity, provenance, completeness and legal custody remain unknown.
No keys or trust relationships are generated.

## Bounds, rejection and recovery

| Resource/control | v1 behavior |
|---|---|
| File format | One UTF-8 JSON file with `.apmcapsule` suffix; begins with `{`; archives and external payloads unsupported |
| Input | At most 4 MiB, including an extra-byte overflow check after opening; JSON nesting at most 12 |
| Session | At most 1,000 source-session records including omitted human records; larger exports fail before destination creation |
| Review pages | 1–100 records, original receipt order, complete included-session coverage |
| Citations | At most 100 per record; missing included targets explicitly enumerated in manifest |
| Schema | Exact fields, version/algorithm, canonical UUIDs, integer bounds, evidence-class consistency and monotonic stream/receipt checks |
| JSON attacks | Duplicate keys, noninteger numbers, unknown fields, invalid UTF-8/surrogates and unsafe text rejected |
| Archives | ZIP/path traversal, duplicate-entry and compressed-bomb fixtures rejected before any archive processing; no extraction exists |
| Output failure | New file only; flushed/fsynced on success. An interrupted write may leave a partial file; it is retained and fails verification, never silently repaired |

Import constructs an in-memory `Capsule` context with copy-returning page/resolve/
manifest accessors. It does not insert records into SQLite or create an extraction
directory. All imported classes are **declared** classes; imported OBSERVED must
not be interpreted as an observation made by the receiving installation.
Source export uses the existing read-only verified snapshot and its bounds.

## Two-session investigation

The [comparison module](../apm/evidence/compare.py) requires distinct sessions.
It compares final command outcome reports by normalized source, declared evidence
class and optional explicit `comparison_key`; an absent key is UNSPECIFIED.
Different task labels and synthetic versus reported evidence stay separate.
Matching labels/codes indicate resemblance, not the same command or cause.

Results carry scoped references `(capsule SHA-256, session UUID, event UUID)`,
outcome counts, common nonzero codes, alternatives, unknowns and a proposed human-
authorized check. Within-session incompatible final outcomes for the same declared
stream/source/class, observed turn and item are labelled CONTRADICTED. A reported
new turn separates reused item IDs. Missing boundaries limit this inference.
Different outcomes in different sessions alone are not contradictions.

The output includes at most 40 matching groups, 40 contradiction groups and 20
cited records per side/group, with totals/truncation disclosed. The full capsule
remains available for paging. No comparison hypothesis is saved as an observed
fact, no experiment is executed, and causal assessment remains **INSUFFICIENT
EVIDENCE**. This is an initial deterministic comparison, not persistent semantic
memory, human-validated learning or multi-agent cooperation.

See [current results](ENGINEERING_PROGRESS.md), [security](../SECURITY.md) and
[the staged architecture](COGNITIVE_ARCHITECTURE.md).
