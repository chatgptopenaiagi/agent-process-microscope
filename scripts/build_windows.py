"""Allowlist source build, no installers or remote publication. Use a pinned venv."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--restricted-temp-compat', action='store_true', help='Explicit build-only inherited-permission temp accommodation; does not change global ACLs')
    args = parser.parse_args()
    destination = args.destination.resolve()
    if sys.platform != 'win32' or platform.machine() != 'AMD64': raise RuntimeError('Windows x64 build required')
    if not destination.is_relative_to(ROOT / 'cache') or destination.exists(): raise ValueError('Choose a NEW project cache directory')
    expected = {}
    for line in (ROOT / 'packaging/build-requirements.txt').read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            name, version = line.strip().split('=='); expected[name] = version
            if metadata.version(name) != version: raise RuntimeError('Build dependency version mismatch: ' + name)
    destination.mkdir(parents=True)
    source = destination / 'source'; source.mkdir()
    sources = sorted((ROOT / 'apm').rglob('*.py'))
    sources += [ROOT / p for p in ('pyproject.toml', 'README.md', 'LICENSE', 'NOTICE')]
    inventory = []
    for path in sources:
        if path.is_symlink(): raise ValueError('Source symlink rejected')
        relative = path.relative_to(ROOT)
        target = source / relative; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        inventory.append(dict(path=relative.as_posix(), sha256=digest(target)))
    for name in ('entry.py', 'apm.spec', 'version.txt', 'build_wheel.py'):
        shutil.copyfile(ROOT / 'packaging' / name, source / name)
        inventory.append(dict(path='packaging/' + name, sha256=digest(source / name)))
    env = dict(os.environ)
    env.pop('PYTHONPATH', None); env['PYTHONNOUSERSITE'] = '1'
    env['PYINSTALLER_CONFIG_DIR'] = str(destination / 'freezer-cache')
    env['PYTHONHASHSEED'] = '0'
    def run(arguments, log, timeout=300):
        with (destination / log).open('xb') as output:
            result = subprocess.run([sys.executable, *arguments], cwd=source, env=env,
                stdout=output, stderr=subprocess.STDOUT, timeout=timeout,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode: raise RuntimeError('Build step failed; see ' + log)
    run(['-m', 'PyInstaller', '--noconfirm', '--distpath', str(destination / 'dist'),
         '--workpath', str(destination / 'work'), str(source / 'apm.spec')], 'freezer.txt')
    wheel_dir = destination / 'wheel'; wheel_dir.mkdir()
    run(['build_wheel.py', str(wheel_dir), *(['--restricted-temp-compat'] if args.restricted_temp_compat else [])], 'wheel.txt')
    bundle = destination / 'dist' / 'APM'
    notices = bundle / 'THIRD_PARTY_LICENSES'; notices.mkdir()
    # Full installed license texts, including vendored license notices, are retained.
    for name in expected:
        distribution = metadata.distribution(name)
        for relative in distribution.files or []:
            if '__pycache__' in str(relative) or Path(relative).suffix in ('.py', '.pyc'): continue
            if not any(word in Path(relative).name.lower() for word in ('license', 'copying', 'authors')): continue
            original = Path(distribution.locate_file(relative))
            if not original.is_file(): continue
            target = notices / name / Path(*[part for part in relative.parts if part not in ('.', '..')])
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(original, target)
    python_base = Path(sys.base_prefix)
    python_license = python_base / 'LICENSE.txt'
    if not python_license.is_file(): raise RuntimeError('Python license text unavailable')
    shutil.copyfile(python_license, notices / 'Python-LICENSE.txt')
    for original in sorted((python_base / 'tcl').rglob('license*')):
        if original.is_file():
            target = notices / 'Tcl-Tk' / original.relative_to(python_base / 'tcl')
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(original, target)
    (bundle / 'DEPENDENCIES.json').write_text(json.dumps(dict(build=expected, python=sys.version,
        application_runtime=['Python', 'Tcl/Tk', 'SQLite (public domain)', 'psutil'],
        provenance='Local installed toolchain; not an upstream signature verification',
        release_status='DEVELOPMENT ONLY; clean-machine installation, signing and installer lifecycle unverified'), indent=2))
    (bundle / 'START-HERE.txt').write_text('APM 0.2.0.dev1 — local development build\n\nOpen APM.exe for Holmes Lab. No observation starts automatically.\n'
        'Try the clearly labeled synthetic demonstration. Cases default to your local application-data APM folder.\n'
        'APM-cli.exe provides advanced commands and explicit desktop-check qualification.\n'
        'Keep this entire application folder together. No Codex or Python installation is required by design.\n'
        'Clean-machine qualification and installer lifecycle remain unverified. This build is unsigned.\n'
        'Deleting the portable program folder does not delete separately stored user data.\n', encoding='utf-8')
    files = [dict(path=p.relative_to(bundle).as_posix(), bytes=p.stat().st_size, sha256=digest(p))
             for p in sorted(bundle.rglob('*')) if p.is_file()]
    if any('codex' in f['path'].lower() and not f['path'].endswith('.py') for f in files):
        raise RuntimeError('Unexpected Codex-named artifact')
    if any(Path(f['path']).suffix.lower() in ('.sqlite3', '.db', '.apmcapsule', '.jsonl', '.pem', '.key') for f in files):
        raise RuntimeError('Private evidence or key extension in package')
    (destination / 'artifact-manifest.json').write_text(json.dumps(dict(source=inventory, bundle=files,
        build_dependencies=expected, restricted_temp_compat=args.restricted_temp_compat,
        python=sys.version, platform=platform.platform()), indent=2))
    archive = Path(shutil.make_archive(str(destination / 'APM-0.2.0.dev1-windows-x64-portable'), 'zip', bundle.parent, bundle.name))
    artifacts = [archive, *wheel_dir.glob('*.whl')]
    (destination / 'SHA256SUMS').write_text(''.join(digest(p) + '  ' + p.name + '\n' for p in artifacts), encoding='ascii')
    print(json.dumps(dict(build='COMPLETED', destination=str(destination), bundle_files=len(files), artifacts=[p.name for p in artifacts])))


if __name__ == '__main__': main()
