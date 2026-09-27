# Event model

APM records external evidence in canonical schema version `1.0`. An event says what an adapter or interpreter reported, where the report came from, and how it should be interpreted. It does not claim access to an agent's private thoughts.

The published structure is [event.schema.json](event.schema.json); runtime validation lives in [`apm/core/events.py`](../apm/core/events.py). The schema describes canonical serialized records, including every required field. Python construction and normalization may supply defaults before serialization.

## Canonical fields

| Field | Meaning |
| --- | --- |
| `schema_version` | Canonical format version, currently `1.0` |
| `event_id` | UUID identifying this event |
| `timestamp` | Timezone-aware event timestamp; normalizer-generated timestamps use UTC |
| `session_id` | UUID of the recording session |
| `agent_id` | Session-level label for the observed process or synthetic/imported source |
| `source` | Adapter or interpreter that supplied the event |
| `category` | Validated lowercase category |
| `action` | Validated uppercase action |
| `target` | Redacted textual subject of the action |
| `status` | Evidence status: `observed`, `inferred`, `unknown`, `unavailable`, or `synthetic` |
| `confidence` | Finite number from 0 to 1; an implementation-supplied confidence indicator |
| `interpretation_level` | `observation`, `inference`, or `synthetic` |
| `raw_reference` | Reference supplied by the producer, or a generated digest of sanitized metadata |
| `metadata` | Structured, redacted supporting fields and scope limitations |

Category and action vocabulary includes reserved possibilities such as browser, network, and file-read actions. Their presence in the schema does not mean Genesis implements those observers. The [Genesis status](GENESIS_STATUS.md) lists actual capabilities.

## Evidence status and interpretation

| Status | How to read it |
| --- | --- |
| `observed` | A scoped adapter reported external evidence. Its source and attribution limits still apply. |
| `inferred` | A rule interpreted supporting evidence; `interpretation_level` must be `inference`. |
| `unknown` | The available evidence does not establish a stronger conclusion. |
| `unavailable` | Collection could not supply the requested evidence. This is not proof that activity stopped. |
| `synthetic` | Deliberately generated demonstration data; `interpretation_level` must be `synthetic`. |

Confidence is not a statistically calibrated probability. An observed filesystem change can have confidence `1.0` in the metadata observation while leaving the actor unknown. A recognized test command receives a capped or explicit inference confidence of `0.8`; this does not establish how many assertions ran.

The state engine emits separate `DerivedState` records with state, summary, timestamp, confidence, and supporting event IDs. Those records are interpretations, not canonical events or hidden reasoning transcripts. See [Observability model](OBSERVABILITY_MODEL.md).

## Provenance and references

The normalizer assigns the session and agent identity, validates the canonical event, and supplies `metadata.observation_source` when absent. Without a supplied reference, `raw_reference` is `sha256:` followed by a digest of sanitized metadata. That digest is neither a hash of the entire original source nor a signature proving authenticity.

An inferred live test event references its source event ID and includes `evidence_event_ids`. Imported Codex reports carry `metadata.provenance = imported_codex_report` and `timestamp_basis = import_time`. Import time must not be presented as the original command's execution time. An imported report is not independently verified operating-system evidence.

The UI's **Raw event** pane displays the redacted canonical event JSON. It does not reveal unredacted source bytes, terminal output, private reasoning, or file contents. The **Evidence** pane shows retained metadata and references without opening or executing those references.

## Redaction and retention

Normal live and import flows sanitize before queueing, presentation, and persistence; storage also sanitizes serialized values. The sanitizer excludes designated private-content fields, masks recognizable secret patterns, strips control sequences, and bounds nested structures and text. Redaction is best effort. Paths, timing, tool names, and other metadata can still be sensitive, so recordings should be reviewed before sharing.

Canonical validation checks identity, timestamp, vocabulary, types, finite confidence, and status/interpretation compatibility. Replay additionally checks session membership, duplicate event IDs, malformed JSON, and input bounds. Validation does not authenticate the producer or prove that a plausible event describes something that actually happened.

See [Security](../SECURITY.md) and [Replay model](REPLAY_MODEL.md) for the operational boundaries.
