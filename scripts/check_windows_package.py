"""Independent local artifact checks; does not claim clean-machine installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import struct
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    bundle, destination = args.bundle.resolve(), args.destination.resolve()
    if not destination.is_relative_to(ROOT / 'reports') or destination.exists(): raise ValueError('Choose a NEW project reports destination')
    destination.mkdir(parents=True)
    cwd = destination / 'empty working directory'; cwd.mkdir()
    env = dict(os.environ)
    for key in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'): env.pop(key, None)
    env['PATH'] = str(Path(env.get('SystemRoot', 'C:/Windows')) / 'System32')
    env['LOCALAPPDATA'] = str(destination / 'empty user data')
    env['PYTHONNOUSERSITE'] = '1'
    results = {}
    hashes = {p.relative_to(bundle).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in bundle.rglob('*') if p.is_file()}
    for name, subsystem in (('APM.exe', 2), ('APM-cli.exe', 3)):
        exe = bundle / name
        data = exe.read_bytes(); pe = struct.unpack_from('<I', data, 0x3c)[0]
        assert data[pe:pe+4] == b'PE\0\0'
        assert struct.unpack_from('<H', data, pe+4)[0] == 0x8664
        assert struct.unpack_from('<H', data, pe+24+68)[0] == subsystem
        target = destination / name.replace('.exe', '-check')
        with (destination / (name + '.txt')).open('xb') as log:
            completed = subprocess.run([str(exe), 'desktop-check', str(target)], cwd=cwd, env=env,
                stdout=log, stderr=subprocess.STDOUT, timeout=60,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        assert completed.returncode == 0, name + ' failed'
        result = json.loads((target / 'result.json').read_text())
        assert result['status'] == 'PASSED' and result['frozen'] and result['source_hashes_unchanged']
        assert Path(result['module_location']).resolve().is_relative_to(bundle)
        case = next((target / 'data/demonstrations').glob('*/investigation.sqlite3'))
        connection = sqlite3.connect(case.as_uri() + '?mode=ro', uri=True)
        previous, count = '0' * 64, 0
        try:
            for body, prior, tip in connection.execute('SELECT body,previous,fingerprint FROM entries ORDER BY seq'):
                assert prior == previous
                assert hashlib.sha256(b'APM-Holmes-journal-v1\0' + bytes.fromhex(prior) + body).hexdigest() == tip
                previous, count = tip, count + 1
        finally: connection.close()
        assert count == 4 and previous == result['integrity']['tip']
        results[name] = dict(status='PASSED', architecture='AMD64', subsystem=subsystem,
            independent_chain_check=True, **{k:result[k] for k in ('seconds', 'revisions', 'citations_resolved', 'source_hashes_unchanged')})
    assert hashes == {p.relative_to(bundle).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in bundle.rglob('*') if p.is_file()}, 'Bundle changed during acceptance'
    with zipfile.ZipFile(args.wheel) as wheel:
        names = wheel.namelist()
        assert len(names) == len(set(names))
        assert all(not p.startswith('/') and '..' not in Path(p).parts for p in names)
        assert all(p.startswith('apm/') or '.dist-info/' in p for p in names)
        assert not any(Path(p).suffix in ('.sqlite3', '.db', '.apmcapsule', '.exe', '.dll', '.pyd', '.jsonl') for p in names)
        assert wheel.testzip() is None
    final = dict(status='PASSED', executables=results, bundle_unchanged=True,
        wheel_structure_checked=True, wheel_install='NOT_CHECKED_BY_THIS_SCRIPT',
        python_and_git_removed_from_child_PATH=True, source_imports_absent=True,
        clean_machine_install='UNVERIFIED', visible_acceptance='UNVERIFIED',
        installer_upgrade_uninstall='UNVERIFIED', result_scope='Local host; automated withdrawn native Tk workflow')
    (destination / 'result.json').write_text(json.dumps(final, indent=2), encoding='utf-8')
    print(json.dumps(final, indent=2))


if __name__ == '__main__': main()
