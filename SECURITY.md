# Security and privacy

Portable software qualification is an explicit engineering action, separate from
passive capsule review. The verifier requires an operator-selected checksum and
external reviewed file manifest, checks archive paths and resource limits before
execution, and never treats imported case content as an execution grant. Hashes
do not establish publisher authenticity. See
[qualification boundaries](docs/INDEPENDENT_QUALIFICATION.md). Do not use the
qualification execution flag for unreviewed downloads. Generated logs, build
inventories with local context, synthetic case databases and qualification reports
stay outside Git. No global permissions are weakened for tests or packaging.

## Reporting a suspected vulnerability

Do not include credentials, private agent sessions, unrestricted command output,
or recordings from real sensitive work in a public issue. Prefer a small
synthetic reproduction that demonstrates the problem without exposing anyone's
data. A private repository can become public later; review attachments either way.

Use an existing private contact channel with the maintainers when one is
available. No dedicated private reporting channel is currently advertised here.
If you have no private contact, open a sanitized issue requesting a reporting
channel, without sensitive vulnerability details, then wait for the maintainers
to provide one. Do not assume a public issue or pull request is private.

Include the affected APM version or commit, operating system, Python version,
expected boundary, observed behavior, and a synthetic reproduction when safe.
If a credential has already been exposed, revoke or rotate it through its issuer;
editing the issue alone does not make the credential safe again.

## Collection and trust boundaries

APM is visible, local and scoped to a selected process tree and workspace. It has
no startup registration, installed service, upload, keylogging, injection,
credential access, browser control, private Codex-history reader or model API call.
Closing/stopping attach observation never kills the observed agent.

The optional `serve` command explicitly opens a bounded `127.0.0.1` TCP receiver.
It requires separate session-scoped reader/reporter capabilities. It has no SQL,
shell or process-control operation. Normal GUI startup opens no listener.
Capability files and SQLite memory inherit filesystem permissions and are
plaintext; this is not isolation from processes able to read those files. Tokens
authorize an API scope, not the truth or OS identity of a producer. New observations
also write SQLite memory; local decisions are opinions, never execution grants.
See [protocol, bounds and trust limitations](docs/OBSERVATORY.md).

The separately invoked `scripts/qualify_codex.py` development harness launches an
explicitly owner-authorized disposable workload through a pinned Codex executable.
The CLI may contact its configured provider. The harness does not inspect credentials,
edit global configuration or expose execution through APM's receiver/GUI. It keeps
only allowlisted action reports and fixed startup diagnostic labels, stopping host
observation before cleaning up its own process generations. Its raw artifacts are
private local evidence; publish reviewed aggregate summaries only.

Collection minimizes data before central redaction: file contents, root agent
arguments, environment variables, unrestricted command outputs and private model
reasoning are not retained as observation evidence. The explicitly selected Codex
export is parsed in memory, and its excluded content is discarded. Codex import
uses a strict field/item allowlist; it does not alter or sanitize the original file.
Filesystem excludes secret locations, dependency trees and reparse points. Git
queries exclude patch text and external diff/textconv execution.

The normalizer redacts common secret assignments/flags, bearer/basic authorization,
cookies, API key/token patterns, private keys and URL credentials before events
reach queues, the GUI or the recorder. Imported canonical sessions are sanitized
again. Synthetic redaction tests use fake credentials only. Regex redaction is
best effort: it cannot identify arbitrary secrets hidden in unconstrained text.
Do not deliberately record sensitive workspaces or export sessions without review.

Session storage uses the current user's existing filesystem access rules; it is
not encrypted and does not change machine ACLs. Treat session paths, filenames and
timing metadata as potentially private. Generated sessions, reports and environments
are excluded from Git. Recordings are retained until the owner removes them.

Observation is not a security sandbox. A selected process may itself be malicious;
polling has race windows and cannot enforce its behavior. APM neither grants agent
permissions nor controls agent actions. Attach cannot promise attribution of file
changes, complete process history or exact exit codes. Imported reports are claims
made by their producer, not cryptographic proof.

## Reviewing material before sharing

Inspect filenames, paths, process identifiers, timestamps, workspace names, and
screenshots as well as obvious tokens. APM's pattern redaction is not permission
to publish an arbitrary recording. Share a deliberately synthetic example whenever
possible. Keep generated recordings, local reports, environments and exports out
of commits; do not bypass ignore rules to attach real sessions to a pull request.

## Capsule and cognitive investigation threat model

The offline capsule boundary accepts hostile bytes, not trusted instructions.
Import creates a bounded read-only context and no database rows, files, network
connections, subprocesses or permission grants. Its native viewer explicitly labels
source classes as exporter declarations. No observation engine or protected Codex
component is modified. See [the contract](docs/CAPSULES.md).

| Threat | Implemented control and remaining limit |
|---|---|
| Tampered payload/manifest | Recompute both SHA-256 checksums and reject mismatch; an attacker can recompute unkeyed checksums, so source authenticity remains unknown. Optional external whole-file digest detects replacement |
| Fabricated evidence/provenance | Closed schema, class/sequence/count/reference consistency; declared provenance never becomes a receiving-host observation. These checks cannot establish truth |
| Archive traversal/bombs/duplicate entries | All archives rejected as unsupported JSON before extraction; no archive loader or remote payload fetch exists |
| Malformed metadata/resource exhaustion | 4-MiB bounded read, depth 12, 1,000 source records, 100 citations/record, integer/UUID/text bounds and duplicate-key rejection. Native import is synchronous within these small bounds; no adversarial latency SLA |
| Sensitive disclosure | Minimal allowlist strips free text and human records by default. Separate explicit flags opt in. UUIDs/timestamps/digests remain disclosed; pattern redaction is best effort and manual sharing review is still required |
| Prompt injection/confused deputy | Text only; no execution, model call, interpreter, action grant or network access in capsule APIs. Human opinions and proposed checks confer no authority |
| Replayed/duplicate capsule | No ledger insertion or execution side effect; same-session comparison refused. There is no federated replay-protection protocol yet |
| False matches/causal overclaim | Explicit source/class/task grouping, scoped citations, alternatives, gaps, truncation and INSUFFICIENT EVIDENCE. Synthetic and reported classes do not form one contradiction group |
| Evidence overwrite/corruption | Exclusive new export file; read-only source snapshot; import never writes source or an extraction tree. Interrupted output may remain partial and must fail verification |
| Supply-chain compromise | No added runtime dependency; public structural schema and stdlib validator. Signing, SBOM generation and independently tested distribution remain separate work |
| Unauthorized providers/remote monitoring/cost | No provider, remote pairing or paid request implemented. Future bridges must default off with explicit credentials, budget, cancellation and permission scopes |
| Database incompatibility | Existing SQLite/Genesis formats unchanged; capsule version/algorithm is closed and unsupported versions fail explicitly |

New tests exercise malformed JSON/archives, rehashed structural lies, unsigned
replacement versus external digest, no overwrite, missing references, source
preservation and citation resolution. A professional interface or a passing local
test does not establish laboratory certification, legal custody or complete
coverage. Keys, trust roots, peer pairing and revocation are not activated.

## Holmes journal boundary

Hypotheses and reviews append to a separate, explicitly selected SQLite journal.
Sources remain read-only. A citation binds capsule digest, session and event;
dangling support/contradiction citations are rejected, while missing evidence has
an explicit representation. Declared agent responses cannot submit human review
through the API. A caller's HUMAN_RECORDED declaration is not proof of identity.
Synthetic automated reviews are labeled and cannot promote patterns matching real
evidence classes. Every entry retains `execution_authority: NONE`.

Unique request IDs prevent duplicate append effects; expected revisions reject
stale edits. Transactions and online backup preserve committed history. Append-only
triggers protect against accidental updates/deletes, not an owner rewriting the
database. Unkeyed chains, format/index checks and optional expected tips detect
changes within their stated scope; neither journal nor capsule checks authenticate
provenance. Reports verify/read one snapshot to avoid a concurrent-append tip race.

Imported journal text is rechecked for redaction before display. Byte, count, schema,
SQL length, lock and verification limits bound work. No attached databases or
extension loading is enabled. The GUI has one active worker job and no growing
submission queue. Full hostile-file latency and maximum-size benchmarks remain
unqualified. Backups and reports use new destinations; interrupted files can remain
incomplete and must be rejected or reviewed, never silently reused as valid output.

HTML escapes evidence and uses generated fragment links, a restrictive CSP and no
scripts/external assets. Reports exclude raw sessions and event free text, but
user-authored claims and identifying metadata may still be private. Export is not
publication authorization. Pattern matching is explicit and source-class scoped;
later adverse reviews suspend old patterns. Agreement between offline assessment
messages is not proof. No paid provider, network connection, credential reader,
remote execution, automatic investigation check or action-grant API is introduced.

## Desktop and development packaging

Welcome and normal startup perform no observation or provider connection. Only an
explicit demonstration request creates synthetic evidence in a new directory.
Case opening does not scan for missing source capsules. Completed worker callbacks
are released on Tk's thread; closing waits for an active operation before destroying
the window. Reports retain human-authored content and require review before sharing.

Installed data defaults are separate from program files. Build/check tools accept
new project-local destinations, pin copied distributions and use a source allowlist.
No Codex executable, configuration, authentication or private evidence is bundled.
The optional restricted-temp accommodation is process-local and scoped to new
isolated build/check directories; it changes no existing or global ACL. Local
RECORD/hash checks are not upstream artifact authentication. Transitive binary
redistribution, signing and clean-machine lifecycle checks remain release gates.
