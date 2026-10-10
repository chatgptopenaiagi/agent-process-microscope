# Windows distribution assessment

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
