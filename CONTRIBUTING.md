# Contributing

APM observes external actions and keeps evidence separate from interpretation.
Changes should preserve that distinction and state uncertainty when evidence is
missing. Read [ARCHITECTURE.md](ARCHITECTURE.md), [SECURITY.md](SECURITY.md), and
[LIMITATIONS.md](LIMITATIONS.md) before changing collection or replay behavior.

## Local development

Windows with Python 3.14 and Tk is the exercised development environment. Create
an isolated environment in your checkout; no global PATH or agent configuration
changes are needed.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe scripts\run_checks.py
```

The checks use synthetic data and owned local process/repository fixtures. They
do not need credentials or a paid model call. UI tests require a working Windows
desktop and Tk; report skips or unavailable checks rather than counting them as
passes. Generated test reports stay local and are ignored by Git.

## Engineering expectations

- Scope observers to the selected process tree or workspace. Do not inspect
  private agent histories, authentication files, unrelated command lines or file
  contents to fill an evidence gap.
- Minimize fields before redaction, then normalize before queueing, displaying or
  persisting. Use synthetic canaries to test privacy boundaries.
- Keep replay and import passive. A recorded command is data, never an instruction
  to execute. Imported reports must not be presented as independently verified
  operating-system events.
- Bound helper processes, output, scans, queues and storage. Background helpers
  must avoid foreground console windows and have observable failure/cleanup paths.
- Stopping an attached observer must leave the observed process running. Report
  dropped data, incomplete scans and unavailable capabilities explicitly.

## Submitting a change

Describe the user-visible problem, the resulting behavior, and the checks you
ran. Add focused regressions for meaningful failures or privacy boundaries;
update capability documentation when behavior changes. Keep unrelated formatting
or dependency changes separate.

Review the complete diff and every attachment before submitting. Use synthetic
reproductions rather than real recordings. Do not include credentials, session
exports, environments, caches, generated reports, wheels or private machine
diagnostics. Refer security-sensitive reports to [SECURITY.md](SECURITY.md).

The project's license is [Apache License 2.0](LICENSE). These engineering
guidelines describe how to contribute; they do not add license restrictions or
require a contributor license agreement.
