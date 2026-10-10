"""Install a selected wheel offline into a NEW disposable environment and qualify it.

Run with the pinned build Python. Only pip and psutil are copied from that isolated
environment; the APM package itself must be installed by pip from the wheel.
"""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--restricted-temp-compat', action='store_true')
    args = parser.parse_args()
    directory = args.destination.resolve()
    if not directory.is_relative_to(ROOT / 'cache') or directory.exists(): raise ValueError('Choose a NEW project cache destination')
    directory.mkdir(parents=True)
    environment = directory / 'venv'
    venv.EnvBuilder(with_pip=False).create(environment)
    site = environment / 'Lib/site-packages'
    for name, version in [('pip', '26.2.1'), ('psutil', '7.2.2')]:
        distribution = metadata.distribution(name)
        if distribution.version != version: raise ValueError('Dependency version mismatch')
        base = Path(distribution.locate_file('')).resolve()
        for relative in distribution.files or []:
            source = Path(distribution.locate_file(relative)).resolve()
            if not source.is_relative_to(base) or '__pycache__' in source.parts or source.suffix == '.pyc': continue
            target = site / source.relative_to(base)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists(): raise ValueError('Dependency collision')
            shutil.copyfile(source, target)
    python = environment / 'Scripts/python.exe'
    work = directory / 'empty working directory'; work.mkdir()
    temp = directory / 'temp'; temp.mkdir()
    env = dict(os.environ)
    for key in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'): env.pop(key, None)
    env['PYTHONNOUSERSITE'] = '1'
    env['PIP_CONFIG_FILE'] = os.devnull
    installer = directory / 'install.py'
    installer.write_text('''import os, sys, tempfile
from pathlib import Path
scope = Path(__file__).resolve().parent
tempfile.tempdir = str(scope / 'temp')
if sys.argv[1] == 'compat':
    original = os.mkdir
    def mkdir(path, mode=0o777, *, dir_fd=None):
        if os.name == 'nt' and mode == 0o700 and Path(path).resolve().is_relative_to(scope): mode = 0o777
        return original(path, mode, dir_fd=dir_fd)
    os.mkdir = mkdir
from pip._internal.cli.main import main
raise SystemExit(main(['--isolated', 'install', '--no-index', '--no-deps', '--disable-pip-version-check', sys.argv[2]]))
''', encoding='utf-8')
    def run(command, log):
        with (directory / log).open('xb') as output:
            result = subprocess.run(command, cwd=work, env=env, stdout=output, stderr=subprocess.STDOUT,
                timeout=60, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode: raise RuntimeError('Wheel check failed: ' + log)
    run([str(python), '-I', str(installer), 'compat' if args.restricted_temp_compat else 'standard', str(args.wheel.resolve())], 'install.txt')
    run([str(python), '-I', '-m', 'apm', 'desktop-check', str(directory / 'acceptance')], 'acceptance.txt')
    run([str(environment / 'Scripts/apm.exe'), '--help'], 'entrypoint.txt')
    result = json.loads((directory / 'acceptance/result.json').read_text())
    assert result['status'] == 'PASSED' and not result['frozen']
    assert Path(result['module_location']).resolve().is_relative_to(site)
    assert (environment / 'Scripts/apm-gui.exe').is_file()
    (directory / 'result.json').write_text(json.dumps(dict(status='PASSED',
        wheel_sha256=hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
        pip_install='VERIFIED_IN_DISPOSABLE_VENV', restricted_temp_compat=args.restricted_temp_compat,
        source_imports_absent=True, console_entrypoint=True, gui_entrypoint_created=True,
        native_widget_workflow=True, revisions=result['revisions'], source_hashes_unchanged=result['source_hashes_unchanged'],
        ordinary_owner_install='PENDING_OWNER_EXECUTION', clean_machine_install='UNVERIFIED'), indent=2), encoding='utf-8')
    print((directory / 'result.json').read_text())


if __name__ == '__main__': main()
