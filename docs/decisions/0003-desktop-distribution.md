# ADR 0003: guided native desktop and inspectable portable build

Status: implemented development slice; distribution acceptance remains conditional.

Keep the Python/Tk, stdlib and psutil architecture. The default desktop opens
Holmes Lab with a welcome page and guided evidence/explanation/review/report steps.
The original microscope and passive replay remain available. No observation or
provider connection starts on opening the application. The capsule and journal
schemas do not change; interpretation reports gain readable presentation and
application-version metadata without removing existing JSON fields.

Installed writable data belongs in the per-user APM folder, independent of the
current directory and program files. Explicit paths remain authoritative. Existing
source observation defaults remain compatible. We neither migrate nor delete data.

Select PyInstaller one-folder for the first Windows x64 portable experiment. It
can use the installed Python/Tk toolchain, makes binary contents inspectable and
avoids one-file temporary extraction under the known restricted token. A shared
analysis supplies a desktop and a console executable. Build inputs are an explicit
source allowlist in a new isolated directory, never the repository wholesale.

The pinned build environment is separate from the application environment. The
offline preparation helper copies only named installed distributions, checks their
local RECORD hashes and retains licenses/inventory. This verifies consistency with
local metadata, not upstream supply-chain authenticity. Release preparation must
add an independently obtained, hash-pinned dependency source and clean runner.

Alternatives: Nuitka adds a C compiler and a second compilation toolchain; its
installed release uses AGPL terms with a generated-binary exception. cx_Freeze is
not installed and would add an untested parallel packaging route. WiX can supply a
proper per-user installer later, but installed WiX 7 requires explicit EULA
acceptance and an applicable maintenance-fee determination. Neither is inferred
from permission to build locally. No installer is claimed from a portable archive.

No Codex binary, auth/configuration, private observation or journal belongs in the
package. No release upload, signing identity, auto-update, service, global PATH
change or start-at-login behavior is introduced. Clean-machine installation,
visible usability, upgrade, uninstall and data retention require independent gates.

See [distribution](../DISTRIBUTION.md) for actual tools/results and primary sources,
and the [desktop guide](../DESKTOP_GUIDE.md) for the human workflow.
