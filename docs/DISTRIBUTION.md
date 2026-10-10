# Windows distribution assessment

## Current desktop development qualification — 0.2.0.dev1

Local Windows x64 portable executables and a developer wheel have now been built.
They are **development artifacts, not published downloads or an installer**. The
earlier assessments below remain historical records. No GitHub Release is created.

Selected tool: PyInstaller 6.22.3, one-folder, with a GUI executable and a console
executable sharing the same bundled application. Python 3.14.7 AMD64, Tcl/Tk 9,
SQLite and psutil 7.2.2 supply the runtime. The app has no mandatory AI provider,
Codex or Git dependency for offline investigation. See the [desktop guide](DESKTOP_GUIDE.md).

### Reproduce locally

Use a new directory for every build. `packaging/build-requirements.txt` pins nine
build/runtime distributions; only psutil is an application dependency. With an
authorized package source, install those pins into a project-local environment.
When networking is unavailable, the reviewed offline alternative is:

```powershell
.venv/Scripts/python.exe scripts/prepare_build_env.py cache/build-env-NEW --tools-site <installed-tools-site-packages> --runtime-site .venv/Lib/site-packages
cache/build-env-NEW/Scripts/python.exe scripts/build_windows.py --destination cache/build-NEW
.venv/Scripts/python.exe scripts/check_windows_package.py --bundle cache/build-NEW/dist/APM --wheel cache/build-NEW/wheel/agent_process_microscope-0.2.0.dev1-py3-none-any.whl --destination reports/package-check-NEW
cache/build-env-NEW/Scripts/python.exe scripts/check_wheel.py --wheel cache/build-NEW/wheel/agent_process_microscope-0.2.0.dev1-py3-none-any.whl --destination cache/wheel-check-NEW
```

The offline copy verifies installed RECORD hashes and records all copied files;
it does not establish upstream authenticity. The environment does not inherit
global site-packages. No global package installation or Codex change occurs.
The source build allowlist contains application Python files, package metadata,
license/readme files and the explicit packaging recipe. It excludes sessions,
databases, reports, credentials, build caches and protected agent binaries.

The unmodified wheel backend failed while creating its private temporary output
directory under the restricted token. The explicit `--restricted-temp-compat`
option on the build and wheel-check scripts uses inherited permissions **only for
new temporary directories inside the selected isolated build/check directory and
only in that process**. It changes no existing ACL or global setting. This was
needed for the successful local build/install. Record use of this flag; it is not
evidence of ordinary owner-shell success. Preserve original failed build output.

The resulting `artifact-manifest.json` records every source and bundled file;
`SHA256SUMS` hashes the portable ZIP and wheel. The ZIP contains the complete APM
folder; keep it together and open `APM.exe`. `APM-cli.exe desktop-check <NEW-folder>`
runs a bounded, explicitly synthetic qualification. Nothing executes on normal
startup. Build scripts and pins support repeatability; byte-for-byte reproducibility
across independent builders is **UNVERIFIED** (timestamps/toolchain provenance remain).

### Actual acceptance scope

Both AMD64 executables passed the withdrawn native Tk investigation workflow from
an empty working directory with Python/Git removed from their process PATH. Their
module paths resolve inside the bundle. Two capsules, two citations, challenge,
review/correction, reopening, four revisions and HTML/JSON exports were checked.
An independent parent process recomputed the journal chain. Evidence and program
folder hashes remained unchanged. The wheel was installed by pip without a network
into a fresh disposable venv and passed the same workflow from its installed path.
These are current-host checks, not a clean-machine or visible-human qualification.

| Gate | State and exact scope |
|---|---|
| BUILD VERIFIED | Local one-folder executables and wheel; source/content manifests and SHA-256; restricted-temp flag recorded |
| INSTALL VERIFIED | Wheel pip installation in disposable venv only; normal owner execution pending; Windows installer UNVERIFIED |
| LAUNCH VERIFIED | GUI-subsystem and console-subsystem executables run automated native widgets outside source tree; visible interaction UNVERIFIED |
| UNINSTALL VERIFIED | UNVERIFIED; no installer created or installed |
| DATA PRESERVATION VERIFIED | Source capsule/database hashes and journal history across desktop reopening; installer upgrade/uninstall UNVERIFIED |

### Tool and redistribution review

The [PyInstaller license exception](https://pyinstaller.org/en/stable/license.html)
permits distribution of bundled applications under their own terms. The installed
hook collection uses GPL-2.0-or-later for build hooks and Apache-2.0 for runtime
hooks. Build pins include altgraph (MIT), packaging (Apache-2.0 OR BSD-2-Clause),
pefile (MIT), pywin32-ctypes (BSD-3-Clause), setuptools and pip (MIT), and psutil
(BSD-3-Clause). Copies of installed licenses, including vendored notices, are
retained with the development bundle. Python's installed license and Tcl/Tk terms
are included. SQLite declares its code [public domain](https://sqlite.org/copyright.html).

The generated binary inventory also includes Python extension libraries, OpenSSL,
libffi, Tcl dependencies, compression libraries and Microsoft runtime components.
**A complete version-to-license/redistribution mapping for those transitive binaries
is still a release gate.** The Python Windows license contains additional Microsoft
redistribution requirements. Local build acceptance does not settle public binary
redistribution, signing or publisher identity. No binaries are included in source
publication candidates.

Nuitka 4.2.2 is installed but was not selected: it introduces a C compilation
toolchain and a second packaging route. Its current
[license and generated-code terms](https://nuitka.net/doc/download.html) need their
own review if adopted. [cx_Freeze](https://cx-freeze.readthedocs.io/en/latest/index.html)
is an alternative with Python 3.14 support, but is not installed or tested here.

WiX 7.0.0 is installed. Its [EULA/maintenance terms](https://docs.firegiant.com/wix/osmf/)
require explicit acceptance and an applicability/payment determination. No EULA
acceptance, sponsorship, global WiX setting or installer operation was performed.
Installer work is **BLOCKED pending that owner decision**. The intended design is
per-user application files and Start-menu shortcuts, no services or global PATH
change, and no installer ownership of investigation data. Actual MSI creation,
ordinary-user install/upgrade/rollback/uninstall and data retention remain UNVERIFIED.

**Next task:** qualify this portable build in a clean ordinary-user Windows x64
environment without Python, using the visible demonstration checklist and retained
case hashes. Then close the transitive binary-license and installer decision gates
before authoring and testing the per-user installer. Release publication is separate.

## Historical source-only assessment

Assessment date: 2026-10-10. This is a source engineering checkpoint, not a
downloadable product. No executable bundle, installer, wheel or GitHub Release
was built, installed, signed or published during this milestone. Android is a
separate future phase.

## Available tools

Read-only version probes found PyInstaller 6.22.3, WiX 7.0.0 and setuptools
84.0.0 in existing workstation tool installations. APM's isolated Python 3.14.7
x64 environment contains psutil 7.2.2 but no installed PyInstaller, setuptools,
wheel or `build` distribution. A module-presence probe initially found the local
`build/` namespace; `python -m build --version` and distribution metadata checks
confirmed this is not the build frontend. Tool presence/version is not a successful
packaging qualification. No packages or global configuration were changed.

## Required engineering before delivery

| Target | Proposed route | Acceptance requirement |
|---|---|---|
| Standalone Windows x64 application | An isolated, pinned PyInstaller one-folder build containing Python, Tcl/Tk, SQLite and psutil; GUI and console entry points | Run on a clean Windows x64 system without Python; inspect bundled dependencies; exercise observation, passive replay, read-only review and shutdown |
| Windows installer | WiX per-user MSI wrapping the tested bundle | Install, upgrade, rollback and uninstall as a normal user; retain all user recordings and databases; no agent installation/configuration changes |
| Developer installation | Existing setuptools `pyproject.toml` backend, wheel containing only `apm*` packages and license metadata | Install wheel into a fresh isolated environment, resolve psutil, check both entry points and Tk availability, run acceptance from outside the source tree |
| GitHub downloads | Explicitly authorized release of tested assets at a reviewed commit, with SHA-256 manifest | Independent download/hash/install checks; reviewed notes and dependency licenses; no databases, recordings, credentials or machine reports |

The first code prerequisite is a tested writable-data policy. The main window
currently defaults recordings beside the package, while `Launch-APM.pyw` writes
recordings and launch errors beside itself. Those defaults are unsuitable for an
installed application directory. Use a per-user application-data directory for
installed defaults, preserve explicit user-selected paths and existing source
workflow paths, and never move/delete evidence automatically. The frozen entry
point must call the application directly rather than assume a sibling `.venv`.
Missing optional Git must remain visibly unavailable rather than block startup.

Prefer one-folder for the first qualification: its files are inspectable and it
avoids one-file extraction during startup. This is an engineering choice informed
by the [PyInstaller bundle modes](https://www.pyinstaller.org/en/stable/operating-mode.html)
and [build options](https://www.pyinstaller.org/en/stable/usage.html). A single-file
executable can be evaluated later. Build from an explicit source allowlist in a
new ignored workspace; never collect the repository root wholesale. Pin build
tools separately from the only application dependency, psutil. Existing global
tool installations are candidates for an offline isolated toolchain, not a reason
to change them or silently build with unrelated packages.

WiX supports [per-user scope](https://docs.firegiant.com/wix/schema/wxs/packagescopetype/)
and [major-upgrade authoring](https://docs.firegiant.com/wix/schema/wxs/majorupgrade/).
Author stable upgrade identity, versioning, shortcuts and uninstall behavior;
exclude user data from installer-owned components. Validate the current tool's
applicable licensing and extension requirements before adopting the build route.
Do not add services, auto-start entries, global PATH changes or Codex integrations
as installation side effects. Signing and publisher identity need a deliberate
owner-controlled process; neither is currently qualified.

The [Python packaging guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
describes frontend/backend wheel builds. Existing metadata declares Python >=3.12,
psutil >=7,<9, `apm` and `apm-gui` entry points, and Apache license files. These are
declared targets, not a tested Python/Windows version matrix. Exercise supported
Python versions and Windows 10/11 separately, including Unicode paths, paths with
spaces, non-administrator use and an unwritable install directory.

Only after artifact verification should an owner-authorized
[GitHub Release](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)
attach the bundle archive, MSI, wheel, license inventory and SHA256SUMS. Hash final
artifact bytes after any signing. Checksums detect changed downloads; they are
not code-signing or source-authenticity guarantees. Do not publish artifacts under
the current mission's local-only authorization.

**Next implementation:** introduce and test installed per-user data defaults,
then create an isolated offline build recipe and qualify a local one-folder
bundle and wheel. Installer and release acceptance follow those working artifacts.
Visible native review inspection is still required before claiming full GUI
acceptance. See [engineering results](ENGINEERING_PROGRESS.md).

## Holmes checkpoint: artifact acceptance remains separate

Read-only probes again found PyInstaller 6.22.3 and WiX 7.0.0; the isolated APM
environment still has no installed build frontend/backend/freezer. Python 3.14.7
AMD64 and psutil 7.2.2 remain unchanged. No installation was attempted.

| Distribution gate | Current state | Required evidence |
|---|---|---|
| BUILD VERIFIED | UNVERIFIED | Isolated allowlist build, dependency/license inventory, version and SHA-256 manifest |
| INSTALL VERIFIED | UNVERIFIED | Clean ordinary-user Windows x64 installation, without preinstalled Python/Codex |
| LAUNCH VERIFIED | UNVERIFIED for packaged software | Launch installed artifact and exercise observation, replay, review and Holmes; source widget tests do not satisfy this gate |
| UNINSTALL VERIFIED | UNVERIFIED | Remove only installer-owned program files and shortcuts |
| DATA PRESERVATION VERIFIED | UNVERIFIED for installer lifecycle | Before/after user-evidence hashes across install, upgrade, rollback and uninstall |

Source evidence preservation is tested separately and does not satisfy an installer
lifecycle gate. Start-menu integration belongs to the per-user installer, not a
source development helper. The next packaging code change remains per-user data
defaults with explicit-path and legacy-source compatibility tests; then a pinned
one-folder build and wheel, followed by clean-environment lifecycle tests. No
protected Codex binary belongs in a package. Release publication is not authorized.
