# Tkinter ownership repair and verification

Checkpoint D (`b17297ade499af03a847fb58f60c3c93a6bce44f`) failed on
Windows Server 2025 / Python 3.12.10 in [run 38123604920](https://github.com/chatgptopenaiagi/agent-process-microscope/actions/runs/38123604920).
The source job exited with 2147483651 (`0x80000003`), after repeated
`RuntimeError: main thread is not in main loop` and
`Tcl_AsyncDelete: async handler deleted by the wrong thread` diagnostics.
The last visible test was the rejected-capsule desktop test. The Python 3.14
job passed; that pass did not establish correct interpreter ownership.

## Established mechanism

A controlled reproduction on unmodified D creates a Holmes window, submits an
operation that raises `PermissionError`, processes its completion, closes the
window, releases owner references, then collects garbage on a background thread.
Automatic GC is disabled in this diagnostic only, to control collection timing.
Tk finalizers still run normally. No Tcl error is intercepted or discarded.

The failed Future retains its exception. Calling `Future.result()` in the GUI
adds `finish_operation` to the exception traceback. That frame retains both the
window and the same Future: a cycle survives normal window closure. Inspecting
the original traceback confirmed those two reference identities. Eight Tk
variables remained alive after closure and finalized on the collecting worker.
Python 3.14.7 emitted wrong-thread errors and an interpreter-leak warning rather
than the native abort observed on hosted 3.12. The exact original CI object cannot
be identified from the retained text log alone; the controlled ownership defect
is reproduced, while the native 3.12 abort still requires hosted verification.

This is consistent with the documented [Tkinter threading model](https://docs.python.org/3.12/library/tkinter.html#threading-model)
and the stored-exception behavior of [CPython 3.12.10 Future](https://github.com/python/cpython/blob/v3.12.10/Lib/concurrent/futures/_base.py).
It is an application lifetime defect, not a justification for weakening Windows
permissions, removing Python 3.12, or suppressing shutdown diagnostics.

## Implemented boundary

- APM GUI methods and root-creating entry points require the main GUI thread.
  Caller-supplied Tk roots must also be created there.
- Holmes workers return data or a diagnostic class name, never an exception or
  traceback. Expected rejected operations remain visible as FAIL. Owner callbacks
  are retained and invoked only on the owner.
- Submitted internal operations capture catalog/path/data snapshots, not windows.
  Query workers use existing bounded queues; GUI callbacks never enter those queues.
- Memory and qualification windows finish/cancel their owned work before destroying
  Tk. Closing rejects new submissions, drops callbacks on the owner, and cancels
  scheduled polling/close callbacks. Active writes finish rather than being killed.
- Parent windows wait for owned child operations. Microscope variable traces are
  explicitly removed before destruction. Their Tcl registrations otherwise retain
  Python callbacks and closed windows. Unnecessary `root.apm` reference cycles are
  removed.
- No new event system, runtime dependency, observer behavior, evidence schema,
  journal migration, network connection or execution authority is introduced.

Call the window's `close()` and keep the GUI event loop running until `closed`.
Do not destroy its supplied root directly while work is active. Cancellation is
cooperative: a stuck filesystem/OS operation can delay closure; destroying its Tk
owner or killing a journal write is not the fallback. GUI objects are not supported
worker arguments or worker results. Tests or integrations must obey this boundary.

## Executable checks

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe scripts/check_tk_lifecycle.py --destination cache/tk-repeat-new --repeat 5
.venv/Scripts/python.exe scripts/run_sandbox_checks.py
```

Choose a fresh destination. The lifecycle runner alternates the order of the
original rejected-capsule test, preceding permission-error test, complete desktop
workflow, and focused lifecycle regressions. Fresh subprocesses exercise repeated
windows, failed imports, callback errors, forced background collection, variable
lifetimes, close during work, cancellation, parent-child closure and replay errors.
Original finalizers run; stderr is retained. CI rejects known unraisable/Tcl
shutdown diagnostics even with exit code zero. Standard and compatibility outcomes
remain separate. Fixtures contain only synthetic data.

Recovery qualification also rejects incomplete logs, zero tests, duplicate test
summaries, trailing output after the success footer, and skipped-test summaries.
The repair CI standard job requires exactly 172 completed tests; each focused
process requires 11. Update these explicit expectations when reviewed tests are
added. An isolated `OK` line is insufficient. The original lifecycle repair is
preserved; this additional check changes qualification, not GUI behavior.

Both hosted matrix jobs retain Python 3.12 and 3.14 on `windows-2025`, read-only
repository permissions and pinned Actions. The repair branch/PR filters include
the Checkpoint D base. No release or binary upload is added. A local Python 3.14
pass is not hosted Python 3.12 acceptance. Approval/network blockers require an
owner publication handoff, not a bypass.

## Independent histories and acceptance

The repair branch descends from exact D. Mission 007's preserved checkpoint E
(`3477d31ff1f06c86712f0d7fb22e007c04a54376`) remains a separate D descendant.
After the repair passes both hosted jobs at the same commit, integrate it into a
new E descendant by a reviewed merge or additive cherry-pick. Resolve overlapping
Holmes GUI edits explicitly and apply the same boundary to the new guided-window
executor. Re-run E's five workflows and package checks. Do not rewrite either
history or describe the existing E binaries as containing this repair.

Mission 007's additional offline-runtime requirement remains a separate product
gate: standalone runtime inventory, network-unavailable acceptance, standard-user
and clean-machine tests, and licensing review. Neither this source repair nor a
successful local GUI test qualifies a public binary release.
