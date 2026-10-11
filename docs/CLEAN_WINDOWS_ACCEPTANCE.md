# Clean Windows and human acceptance record

Status: **CLEAN MACHINE QUALIFICATION PENDING** and
**HUMAN VISUAL ACCEPTANCE PENDING OWNER REVIEW** until a tester records actual
results. A hosted Server runner, extracted directory or withdrawn Tk test does
not satisfy these gates. No VM/image installation or modification is authorized
by this procedure alone.

Use an explicitly selected disposable Windows 11 x64 machine/VM and a standard
non-administrator account. Confirm no Python, Codex, source checkout or developer
configuration is needed. Record Windows build, account type, display scaling,
artifact version, ZIP SHA-256, tester declaration and date. Do not record credentials.
Use the reviewed ZIP provided by the owner; no public release download is implied.

1. Compare `Get-FileHash -Algorithm SHA256 -LiteralPath <ZIP>` with the separately
   retained checksum. This checks content, not publisher identity.
2. Extract the entire folder to a user-writable location containing spaces.
   Preserve an untouched copy. Do not run from inside Explorer's ZIP view.
3. Double-click APM.exe from Explorer, then launch using a shortcut whose working
   directory differs. No console, administrator prompt, process observation or
   provider connection should start. Record any warning exactly.
4. Read Start: describe in your own words what APM does, what remains unverified,
   where evidence is stored and how to close. Check buttons at 100%, 125%, 150%
   display scaling and minimum/resized window sizes. Record clipping, contrast,
   focus visibility and whether labels are understandable.
5. Choose the synthetic demonstration. Confirm SYNTHETIC labels. Inspect both
   packages; attach a nonzero outcome as support and a zero outcome as contradiction.
6. Create an explanation, write uncertainty, alternatives and proposed checks.
   Challenge it. Confirm citations resolve and timing/ancestry is not described
   as proven cause. Nothing proposed is executed.
7. Record an assessment with a reason; correct it to INSUFFICIENT_EVIDENCE.
   Inspect both revisions. Try keyboard-only Tab/Shift+Tab and Ctrl+O/Ctrl+N.
8. Close APM completely, restart the executable, open the existing case and
   explicitly reopen its capsules. Confirm history and contrary evidence persist.
9. Export HTML and JSON to new filenames. Open HTML offline, inspect its five
   questions, source references, unknowns, synthetic warning and corrections.
   Confirm no remote content is needed. Reusing an existing name must preserve it.
10. Try a deliberately malformed synthetic capsule and an unavailable output
    directory. Record the explanation; the case and evidence must remain intact.
11. Back up the synthetic journal to a new file, reopen the backup, reopen its
    capsules and check citations. Compare capsule hashes before/after.
12. Close cleanly. Copy the portable program to another user-writable directory;
    verify the original case still opens. Removing only this disposable program
    copy must not remove separately stored case data. Do not delete owner evidence.

For each item record PASS / FAIL / BLOCKED / PENDING, steps, observed outcome,
artifact hash and minimal sanitized evidence. Screenshots require intentional
capture of the APM window only and remain outside source control. A screenshot
alone does not certify a workflow. Failed checks prevent an RC claim; signing,
redistribution review and explicit release authorization remain separate.
