# Development capability qualification

This publication summary contains only information needed to interpret the
engineering checks. Detailed machine inventory, neighboring-project findings,
private paths and raw evidence locations are preserved locally and excluded.

| Capability | Verified scope and limits |
|---|---|
| APM environment | Isolated Python 3.14.7 x64, psutil 7.2.2, SQLite 3.50.4 and Tk 9.0; no new runtime dependency |
| Host qualification | Windows 10 was exercised. Windows 11 remains a target, not a completed qualification |
| Protected Codex | Owner-selected CLI `0.156.0-alpha.17`; owner-run public-stream engineering evidence was independently checked as described in [the checkpoint](ENGINEERING_PROGRESS.md). No account identity verification, alternate CLI, installation repair or authentication inspection |
| Restricted development identity | Ordinary inherited-access directories work; Python's Windows `0700` directories fail under the restricted token. Standard and process-local compatibility results are reported separately |
| Local storage and transport | SQLite WAL, bounded loopback TCP, durable outbox, read-only recovery and native Tk are sufficient for this slice |
| Native GUI | Automated widget checks exercise real SQL evidence and saved Ask. Visible/manual inspection is still unverified; Computer Use runtime was not available in the qualification tool session |
| Optional infrastructure | No GPU inference, model server, database service, neighboring-project integration or new framework is required or qualified |

Normal observation does not launch Codex. The explicit development harness is
separate and bounded, uses the existing owner runtime route, and cleans up only
its own process generations after observation stops. It does not alter global
configuration or security controls. Presence of other installed tools or services
does not establish their health and is not needed for this checkpoint.

Keep local environments, temporary fixtures, capability files, session recordings,
databases and reports out of version control. If Git ownership protection requires
an exception, use only a command-local exception for the selected repository;
never change the global ownership policy.

The native review follow-up exercised the complete retained session (100 + 8 rows)
and 21 saved citation links in real withdrawn Tk widgets. Database/WAL hashes
remained unchanged. Visible inspection is still unavailable: the Computer Use
skill requires a `node_repl` runtime not exposed in this tool session.

Read-only packaging probes found PyInstaller 6.22.3, WiX 7.0.0 and setuptools
84.0.0 outside the isolated application environment. The APM venv has no installed
build frontend/backend or freezer. No tools were installed or upgraded and no
distribution artifacts were built. See [packaging assessment](DISTRIBUTION.md).

The Holmes checkpoint rechecked those tool versions without installing anything.
Its native worker/widget workflow passed automated creation, citation lookup,
challenge, review, correction, reopen, report and pagination checks. Visible human
inspection remains unavailable because the required Computer Use `node_repl`
runtime is not exposed. No screenshot or manual visual acceptance is claimed.
The standard-library-only temporary-directory diagnostic again reproduced the
restricted-token `0700` failure; inherited-directory operations passed. No ACL or
global Python setting was changed. [Current results](ENGINEERING_PROGRESS.md).
