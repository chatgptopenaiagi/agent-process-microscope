# Independent Windows qualification

The portable verifier is a separate standard-library script. It does not import
APM or require Codex. Run it only on a build whose source and external inventory
you have reviewed. **An expected checksum is not publisher authentication.**

```powershell
.venv/Scripts/python.exe scripts/qualify_portable.py <portable.zip> --sha256 <retained-sha256> --manifest <external-artifact-manifest.json> --destination reports/qualification-NEW --execute-reviewed-build
```

Without the execution flag it inspects and extracts but reports execution BLOCKED.
Choose a new destination. Logs, synthetic fixtures and JSON/text results remain
there, including failed runs. No old destination is overwritten or automatically
deleted. Do not supply owner evidence as a test fixture. Review reports before
sharing; local results contain paths and machine context and are ignored by Git.

Before execution the verifier checks the supplied ZIP digest, every member against
the external file inventory, Windows path rules, case collisions, special files,
file/directory collisions, encryption, file count, expansion sizes and compression
ratios. The archive is limited to 128 MiB compressed, 256 MiB expanded, 64 MiB per
file, 2,048 entries and 200:1 expansion. Evidence, credentials and protected engine
filenames are denied. Exact allowlisting complements these filename checks; it is
not a malware scanner. A reviewed executable can still be harmful if the review or
trust inputs are wrong. Do not run this verifier on arbitrary downloaded software.

Extraction creates a new directory, copies only verified files with exclusive
creation, and rechecks every digest before execution. The external manifest must
be separate from the archive and selected by the operator. The directory must not
be writable by another actor during qualification; defending against a hostile
same-user process replacing files concurrently is outside this harness's scope.

Each Windows executable runs a bounded synthetic native-widget workflow, with
Python/Git removed from PATH, a different working directory, spaces in paths and
a fresh application-data destination. Each operation has a 60-second timeout.
No real observation or provider is enabled. A parent recomputes the journal chain,
checks review/correction history, citations, reports and unchanged synthetic source
hashes. A second **OS process** reopens each journal using its retained chain tip.
The build, ZIP and external manifest are rehashed. All subprocess exit codes are
recorded; timeout, rejection and missing prerequisites cannot become PASS.

This is same-machine isolation. It does not remove the host's Python installation,
prove standard-user behavior, inspect visible layouts or qualify an installer.
Clean ordinary-user Windows acceptance, human usability, signing, upgrade and
uninstall remain separate gates. The UI automation uses withdrawn Tk windows;
there is no owner-confirmed visual acceptance in this environment.

## Standard suite diagnosis

Run the ordinary command and compatibility command separately, serially:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe scripts/run_sandbox_checks.py
.venv/Scripts/python.exe scripts/diagnose_tempdirs.py
```

The Mission 005 baseline reproduced 135 compatibility passes and an ordinary run
with three failures and 102 error entries. These are exception entries, not 102
independent causes. The retained per-test classification distinguishes 42 direct
fixture I/O errors, 53 cleanup errors, seven Git setup errors and three downstream
assertion failures. Seven Git setup errors reproduce as `git init` being unable to
enter the selected private fixture directory. The same operation succeeds in an
inherited-permission fixture. No repository security configuration is changed.

A standalone probe, importing no APM code, found a restricted Windows token:
`os.mkdir(mode=0o700)` and `tempfile.mkdtemp` created directories but child writes,
enumeration and directory removal failed. An otherwise equivalent `0o777` directory
worked. Python documents special Windows access control for
[`mkdir(0o700)`](https://docs.python.org/3/library/os.html#os.mkdir).
This strongly supports a restricted-token/private-directory interaction. It does
not prove behavior under the owner's ordinary token; that is **PENDING OWNER EXECUTION**.
No ACL, security policy or global Python configuration was altered.

GUI tests previously checked a status-string substring and therefore missed the
friendly permission-error message. They now check an explicit operation outcome;
closing also consumes the worker result. This improves diagnostic accuracy without
pretending that the underlying environment has been fixed. There is no evidence
from these runs of an application storage defect or filesystem race causing the
standard baseline failures. The compatibility pass alone cannot establish that
all ordinary-user behavior is correct.

After the new tests and explicit GUI outcome checks, the full compatibility suite
passes 151 tests. The separate standard command runs 151 tests with **four failures
and 102 error entries**. Three desktop failures now report PermissionError at the
failed operation; the rejected-capsule test stops at its inaccessible demo fixture
instead of proceeding to a later file error. The original three-failure baseline
is retained. No standard-suite success or owner-token result is implied.

## Capability contract

[The manifest](../capabilities/apm-capabilities-v1.json) describes twelve actual
components, their entry points, evidence boundaries, permission requirements and
tests. [Its schema](../capabilities/apm-capabilities-v1.schema.json) is closed and
versioned. `python scripts/verify_capabilities.py` validates the supported schema
subset, version, unique IDs and local source/test references. Unknown schema
keywords fail closed; there is no remote schema loading or new runtime dependency.
TESTED describes associated automated checks, not production certification or API
stability. Portable distribution remains EXPERIMENTAL; clean-machine acceptance
and independently authenticated provenance remain unverified.
