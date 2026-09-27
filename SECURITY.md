# Security and privacy

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
no startup registration, service, network listener, upload, keylogging, injection,
credential access, browser control, private Codex-history reader or model API call.
Closing/stopping attach observation never kills the observed agent.

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
