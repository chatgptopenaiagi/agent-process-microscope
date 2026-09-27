# Genesis limits

- Windows is the exercised target. Cross-platform abstractions do not constitute
  verified WSL/Linux/remote support.
- Attach, demo and passive replay/import work. Managed agent launch is deferred.
- No hidden reasoning, file-content capture, READ detection, keystrokes or browser
  activity. Browser/Joomla, WSL/cloud and GPU adapters remain future work.
- Polling can miss brief processes/changes; metadata equality can hide a content
  change that preserves size and modification time. Workspace changes are not
  attributed to the attached agent. Rename may appear as delete/create.
- Very large workspaces return an explicit incomplete snapshot. Select a smaller
  project/subdirectory; Genesis does not incrementally crawl unlimited trees.
- Attached process exit codes/stdout are unavailable. Test counts appear only in
  synthetic demo data; real test state is conservative runner inference or an
  imported command return status. A zero return status is not a test-count report.
- Git does not show patch content, and untracked file line counts are unknown.
- Sessions are local, plaintext and bounded; redaction cannot guarantee removal
  of arbitrary secrets. The evidence digest does not provide tamper resistance.
- The live view retains 2,000 recent events; the recording may contain more.
- No standalone frozen EXE or signed installer is delivered in Genesis. The
  windowed Python launcher uses the project virtual environment; machine-specific
  shortcuts are not included in the source repository.
- No live paid Codex model invocation was needed or performed. Official stream
  parsing is tested with synthetic protocol records; real process attachment is
  tested against an owned local fixture without reading existing private sessions.
