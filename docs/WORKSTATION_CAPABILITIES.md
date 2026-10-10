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
