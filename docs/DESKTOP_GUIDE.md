# Start an investigation in Holmes Lab

Open APM. Nothing is observed automatically and no model service is connected.
You do not need Codex, an AI subscription or Git to review evidence, keep a case,
compare capsules or export a report. Source installations still require Python;
packaged builds have separate qualification gates in [Distribution](DISTRIBUTION.md).

## Try the demonstration

Choose **Try a synthetic demonstration** on Start. APM creates two small evidence
packages and an empty case in a new local demonstration folder. Every record is
SYNTHETIC: no real command or agent is being observed. Nothing is executed from
the evidence. Starting another demonstration never overwrites the first one.

1. On **Evidence**, select a reported nonzero outcome and choose **Use as support**.
   Choose the other package, select a zero outcome and choose **Use as contradiction**.
2. On **Explanation**, write a possible explanation and what remains uncertain.
   Add alternatives and any proposed checks, one per line. **Save new explanation**
   preserves the selected references in the case.
3. On **Challenge & review**, run the deterministic challenge. Inspect a saved
   citation to see its source and classification. Similarity or timing is not cause.
4. Enter an assessment reason and choose a review state. **Record assessment**
   adds a revision; **Correct earlier assessment** adds another revision without
   erasing the original. Neither action grants permission to execute anything.
5. On **History**, inspect either revision. On **Report**, explicitly choose a new
   HTML or JSON destination. HTML is self-contained for offline reading.

## Your own case

Use **Create a case** or **Open an existing case**. An APM case is a Holmes journal,
separate from an observation database. Select only authorized evidence packages
with **Open evidence capsule**. Up to eight verified packages can be open at once;
records are paged in groups of 100. Opening a package verifies its structure and
internal hashes, not its producer identity, authenticity or completeness.

The latest saved explanation is selected when a case reopens. Open its source
capsules again to resolve citations; paths to private evidence are not silently
reopened or searched. A missing package stays UNAVAILABLE. Advanced JSON contains
full scoped identifiers and integrity details; readable summaries are the default.

The default Windows data folder is `%LOCALAPPDATA%\APM`. Cases you choose elsewhere
stay there. `apm --data-dir <directory>` selects a desktop data location explicitly.
APM does not scan this folder on startup or automatically move old recordings.
The source microscope's existing sessions location is preserved. Installed
microscope defaults use the per-user folder; explicit destinations still win.

**Case → Back up case** writes a new verified journal backup. Source capsules
remain separate. Review your own written interpretations before sharing a report:
minimized exports can still contain sensitive human text. Existing destinations
are never overwritten. Closing the application preserves completed revisions;
if an operation is still running, the window waits for it to finish before closing.

## Advanced tools and accessibility

The Advanced tools menu opens the existing microscope for explicitly configured
observation/replay, or a read-only capsule viewer with session comparison. Each
observer has its own controls. Stopping observation does not kill the selected
process. No external provider is needed for any of these local workflows.

Use Ctrl+N for a new case and Ctrl+O to open one. Tab/Shift+Tab move between fields,
including multiline fields; Enter still adds a line. Evidence classifications and
review states are written as text and do not depend on color. The raw structured
view is optional. Human accessibility and visible layout acceptance remain separate
from automated widget checks.

## Visible acceptance checklist — owner execution pending

- Read the Start screen at normal Windows scaling, then at 125% and 150%.
- Follow the demonstration without consulting code or the command line.
- Confirm every important control fits, text is legible, and keyboard focus is clear.
- Distinguish a source claim, a synthetic record, an inference and an unknown fact.
- Open a real authorized capsule, inspect all pages and a saved citation.
- Record and correct an assessment, close, reopen and inspect both revisions.
- Read the offline HTML report and follow its supporting and contrary citations.
- Confirm a failed import explains that sources were preserved.

Automated withdrawn-window tests do not mark any of these human checks complete.
