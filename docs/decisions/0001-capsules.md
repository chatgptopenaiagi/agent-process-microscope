# ADR 0001: bounded evidence exchange before federation

Status: accepted for the local Capsule v1 implementation, 2026-10-10.

## Context and decision

APM already records evidence in SQLite and reviews complete sessions natively.
The next useful boundary is selective offline exchange that does not require the
original database, model, private histories or a live connection. Keep a modular
monorepo. Add `apm.evidence` beside preserved storage/observation modules; do not
split repositories, migrate evidence or add mandatory dependencies now.

Use a documented single-file JSON profile with explicit version and closed schema,
payload/manifest SHA-256, source declarations, preserved citations and disclosure
metadata. Use original UUIDs and receipt numbers for references; do not pretend a
redacted record has the original content fingerprint. Import into an isolated
read-only context. Reject every archive in v1. A future multi-file container must
have separate archive-safety acceptance before enabling extraction.

## Alternatives and interoperability research

| Candidate and primary source | APM relevance and decision | Security, license and maintenance implications |
|---|---|---|
| [BagIt, RFC 8493](https://www.rfc-editor.org/rfc/rfc8493.html) | Established payload/tag manifest packaging. Candidate outer package for later multi-file capsules; v1 is not BagIt conformant | Checksums do not resist an attacker replacing manifests. Do not implement remote `fetch` behavior. No library/code adopted; future library license and path/decompression controls require review |
| [CASE/UCO](https://caseontology.org/resources/case_design_document.html) | JSON-LD representation of investigation provenance and relationships; preferable future forensic mapping vocabulary | Mapping an APM observation does not establish acquisition authenticity. Do not dereference remote contexts on import. Larger ontology/versioning burden; review chosen ontology/tool release and license before adoption |
| [W3C PROV-O](https://www.w3.org/TR/prov-o/) | Entities, activities and agents inform a future explicit provenance mapping | A provenance assertion remains an assertion. No RDF engine dependency or third-party implementation copied; mapping tests are required before claiming conformance |
| [JSON Schema 2020-12](https://json-schema.org/draft/2020-12) | Public structural contract for independent tools; adopted as a published schema document | The runtime uses closed stdlib validation plus stronger cross-record checks, not a general schema engine. No remote references; adopting a validator later requires a pinned version/license and compatibility tests |
| [OpenTelemetry logs model](https://opentelemetry.io/docs/specs/otel/logs/data-model/) | Distinguishes event and observed timestamps; useful future collector adapter | It is not an evidence-custody or trust system. No collector/SDK added; independently test mappings, clock uncertainty, privacy, overload and SDK license/dependency footprint |
| [MCP authorization](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization) | Future evidence-query tools for configured agents | Tool authorization is separate from claims and execution authority. No MCP registration or server added. Pin a reviewed protocol/SDK version and test confused-deputy, consent and revocation behavior before use |
| [DSSE](https://github.com/secure-systems-lab/dsse/blob/master/protocol.md) | Candidate signing envelope over a typed capsule digest attestation, kept beside the capsule | Signatures need an external trust policy. No cryptographic implementation vendored, dependency adopted or private key created; review the chosen signing library and its license separately |
| [SPDX](https://spdx.dev/use/specifications/) | Dependency inventory for eventual executable/installer releases | An SBOM is not proof of build provenance or safety. Select and test a version/tool only during packaging; no generator added now |

These are comparisons of documented capabilities, not tested integrations. v1
uses its existing explicitly documented Python JSON canonical profile rather
than claiming RFC 8785 compatibility. Only integers are allowed in the exchange
contract, simplifying independent digest calculation. A standards-based future
signature should bind exact bytes and their content type rather than introduce
another ambiguous JSON transformation.

## Detached signatures: design only

Candidate: a separate DSSE envelope whose typed payload states the capsule's byte
SHA-256, format version and disclosure identity. The verifier first validates the
signature with an explicitly paired public key, then compares the attested digest
to the complete capsule bytes, then runs schema/content checks. Capsule-controlled
keys, key URLs or roots must never become trust anchors automatically.

Before implementation, define owner-controlled key creation/storage, public-key
fingerprints, explicit trust scopes, rotation with overlap, versioned trust lists,
revocation publication and offline freshness rules. A revoked or unknown key must
produce an explicit unavailable/untrusted result; historical verification policy
needs trustworthy signing-time evidence, not a self-declared timestamp. Preserve
prior trust decisions for review. The [W3C integrity guidance](https://www.w3.org/TR/vc-data-integrity/)
also distinguishes credential revocation from verification-method status; v1
implements neither. No trusted keys, signing, rotation or revocation are claimed.

## Acceptance and consequences

Executable tests cover independent digest calculation, closed input validation,
malformed archives, disclosed omission, same-session citation lookup, no overwrite,
source database preservation and scoped two-session comparison. Recomputed unsigned
digests intentionally pass internal consistency; a retained external digest rejects
replacement. This explicitly tests the authenticity limit instead of hiding it.

Benefits are inspectability, offline use and a small attack surface. Costs are a
1,000-record/4-MiB exchange limit, omitted source metadata, no external artifact
payloads, no native BagIt/CASE compatibility and no signer identity. Native-view
tests are automated; visible/manual approval is still separate. Existing memory
and Genesis formats do not change. A future format version must retain v1 reading
or explicitly refuse it; never rewrite old capsules during import.
