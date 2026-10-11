"""Qualify an explicitly selected, reviewed Windows portable build, offline.

The expected ZIP hash AND external build manifest are trust inputs supplied by
the operator. Neither proves publisher authenticity. Never use an untrusted
archive's own assertions as permission to execute it. No automatic cleanup:
failed fixtures and logs are retained in the new destination for inspection.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
import struct
import subprocess
import sys
import zipfile

MAX_ARCHIVE = 128 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
MAX_FILE = 64 * 1024 * 1024
MAX_ENTRIES = 2048
FORBIDDEN = {'.sqlite', '.sqlite3', '.db', '.apmcapsule', '.jsonl', '.pem', '.key', '.pfx', '.p12', '.bundle'}
RESERVED = re.compile(r'^(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\.|$)', re.I)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_name(name):
    require(isinstance(name, str) and 0 < len(name) <= 240, 'Invalid member name length')
    require('\\' not in name and ':' not in name and not name.startswith('/'), 'Unsafe member path')
    parts = name.rstrip('/').split('/')
    require(all(p not in ('', '.', '..') and p == p.rstrip(' .') and
                not RESERVED.match(p) and not any(ord(c) < 32 or c in '<>"|?*' for c in p)
                for p in parts), 'Unsafe Windows member name')
    require(parts[0] == 'APM', 'Unexpected archive root')
    return PurePosixPath(*parts)


def prohibited(name):
    p = PurePosixPath(name); lower = str(p).lower()
    return (p.suffix.lower() in FORBIDDEN or
            any(x.lower() in ('.git', '.codex', '.venv', 'sessions', 'recordings', 'reports') for x in p.parts) or
            any(x in lower for x in ('codex.exe', 'credentials', 'auth.json', '.sqlite3-', '.db-')) or
            p.name.lower() == '.env' or p.name.lower().startswith('.env.'))


def inspect_archive(archive, expected_sha256, manifest):
    """Read every member before creating any extracted executable."""
    archive = Path(archive)
    require(re.fullmatch('[0-9a-f]{64}', expected_sha256) is not None, 'Expected SHA-256 required')
    require(archive.stat().st_size <= MAX_ARCHIVE, 'Archive exceeds limit')
    require(digest(archive) == expected_sha256, 'Archive checksum mismatch')
    require(isinstance(manifest, dict) and isinstance(manifest.get('bundle'), list), 'External inventory required')
    require(0 < len(manifest['bundle']) <= MAX_ENTRIES, 'Inventory count invalid')
    expected = {}
    for entry in manifest['bundle']:
        name = 'APM/' + entry['path']; safe_name(name)
        require(not prohibited(name) and name.casefold() not in expected, 'Prohibited or duplicate inventory member')
        require(type(entry['bytes']) is int and 0 <= entry['bytes'] <= MAX_FILE, 'Invalid inventory size')
        require(re.fullmatch('[0-9a-f]{64}', entry['sha256']) is not None, 'Invalid inventory digest')
        expected[name.casefold()] = entry
    seen, files, total = set(), {}, 0
    with zipfile.ZipFile(archive) as z:
        require(0 < len(z.infolist()) <= MAX_ENTRIES, 'Archive entry limit exceeded')
        for item in z.infolist():
            require(item.orig_filename == item.filename, 'Truncated archive member name')
            name = str(safe_name(item.filename)); key = name.casefold()
            require(key not in seen, 'Duplicate or case-colliding archive member'); seen.add(key)
            mode = item.external_attr >> 16
            require(stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR), 'Special archive member rejected')
            require(not item.flag_bits & 1 and item.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'Unsupported archive encoding')
            require(not prohibited(name), 'Prohibited archive content')
            if item.is_dir():
                require(item.file_size == 0, 'Directory contains data'); continue
            total += item.file_size
            require(0 <= item.file_size <= MAX_FILE and total <= MAX_TOTAL, 'Archive expansion limit exceeded')
            require(item.file_size <= max(1, item.compress_size) * 200, 'Archive compression ratio exceeded')
            require(key in expected and expected[key]['path'] == name[4:], 'Member absent from exact reviewed inventory')
            require(item.file_size == expected[key]['bytes'], 'Member size mismatch')
            h, count = hashlib.sha256(), 0
            with z.open(item) as source:
                while chunk := source.read(65536):
                    count += len(chunk); require(count <= item.file_size, 'Expansion exceeds declaration'); h.update(chunk)
            require(count == item.file_size and h.hexdigest() == expected[key]['sha256'], 'Member content mismatch')
            files[name] = dict(bytes=count, sha256=h.hexdigest())
        require({n.casefold() for n in files} == set(expected), 'Missing inventory member')
        for name in files:
            require(not any(str(p).casefold() in {n.casefold() for n in files} for p in PurePosixPath(name).parents), 'File/directory collision')
    require(all('APM/' + n in files for n in ('APM.exe', 'APM-cli.exe')), 'Both application entry points required')
    return files


def extract_checked(archive, files, destination):
    """Exclusive extraction; never calls extractall or overwrites an existing file."""
    destination = Path(destination)
    require(not any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction())
                    for p in (destination, *destination.parents)), 'Linked destination rejected')
    destination.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        for name, expected in files.items():
            target = destination.joinpath(*safe_name(name).parts)
            require(target.resolve().is_relative_to(destination.resolve()), 'Extraction escaped destination')
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(name) as source, target.open('xb') as output:
                count = 0
                while chunk := source.read(65536):
                    count += len(chunk); require(count <= expected['bytes'], 'Extraction exceeds reviewed size'); output.write(chunk)
            require(count == expected['bytes'] and digest(target) == expected['sha256'], 'Extraction changed after inspection')


def validate_case(target):
    """Independently check stored chain, corrections, reports and retained sources."""
    result = json.loads((target / 'result.json').read_text())
    require(result['status'] == 'PASSED' and result['frozen'] and result['source_hashes_unchanged'], 'Workflow did not pass')
    require(result['citations_resolved'] == 2 and result['revisions'] == 4, 'Workflow counts incorrect')
    cases = list((target / 'data/demonstrations').glob('*/investigation.sqlite3'))
    require(len(cases) == 1, 'Unexpected case count'); case = cases[0]
    connection = sqlite3.connect(case.as_uri() + '?mode=ro', uri=True)
    previous, entries = '0' * 64, []
    try:
        for body, prior, tip in connection.execute('SELECT body,previous,fingerprint FROM entries ORDER BY seq'):
            require(prior == previous, 'Broken journal predecessor')
            require(hashlib.sha256(b'APM-Holmes-journal-v1\0' + bytes.fromhex(prior) + body).hexdigest() == tip, 'Broken journal digest')
            entries.append(json.loads(body)); previous = tip
    finally:
        connection.close()
    require(len(entries) == 4 and previous == result['integrity']['tip'], 'Journal checkpoint mismatch')
    require(entries[-1]['kind'] == 'CORRECT' and all(e['execution_authority'] == 'NONE' for e in entries), 'Review history or authority mismatch')
    for name, sha in result['source_sha256'].items():
        require(Path(name).name == name and digest(case.parent / name) == sha, 'Synthetic source changed')
    report = json.loads((target / 'investigation.json').read_text())
    require(len(report['history']) == 4 and len(report['citations']) == 2, 'Report inventory mismatch')
    require(all(c['status'] == 'RESOLVED' for c in report['citations']), 'Report has unresolved citation')
    require(report['execution_authority'] == 'NONE', 'Report authority mismatch')
    html = (target / 'investigation.html').read_text(encoding='utf-8')
    require('What happened?' in html and 'CORRECT' in html and '<script' not in html.lower(), 'HTML report missing or active')
    return case, result


def qualify(archive, expected, manifest_path, destination, *, execute=False):
    destination = Path(destination).resolve()
    require(not destination.exists(), 'Choose a NEW qualification destination')
    destination.mkdir(parents=True)
    result = dict(status='FAIL', scope='Same-machine isolation; not a clean Windows installation',
                  clean_machine='UNVERIFIED', human_visual_acceptance='UNVERIFIED',
                  installer_lifecycle='UNVERIFIED', subprocesses=[], cleanup='Retained owned fixtures and logs')
    try:
        require(Path(manifest_path).stat().st_size <= 2 * 1024 * 1024, 'Manifest exceeds limit')
        manifest = json.loads(Path(manifest_path).read_text())
        files = inspect_archive(archive, expected, manifest)
        result.update(archive_sha256=expected, manifest_sha256=digest(manifest_path), archive_files=len(files), archive_inspection='PASS')
        extract_checked(archive, files, destination / 'portable application')
        bundle = destination / 'portable application/APM'
        result['extraction'] = 'PASS'
        if not execute or sys.platform != 'win32':
            result.update(status='BLOCKED', execution='Explicit --execute-reviewed-build and Windows required')
            return result
        cwd = destination / 'unrelated working directory'; cwd.mkdir()
        env = dict(os.environ)
        for k in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'): env.pop(k, None)
        env['PATH'] = str(Path(env.get('SystemRoot', 'C:/Windows')) / 'System32')
        env['PYTHONNOUSERSITE'] = '1'
        def run(arguments, label):
            with (destination / (label + '.txt')).open('xb') as output:
                try:
                    p = subprocess.run(arguments, cwd=cwd, env=env, stdout=output,
                        stderr=subprocess.STDOUT, timeout=60, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                except subprocess.TimeoutExpired:
                    result['subprocesses'].append(dict(operation=label, status='FAIL', timeout=True)); raise
            result['subprocesses'].append(dict(operation=label, exit_code=p.returncode))
            require(p.returncode == 0, 'Packaged operation failed: ' + label)
        for name, subsystem in (('APM.exe', 2), ('APM-cli.exe', 3)):
            exe = bundle / name; data = exe.read_bytes(); pe = struct.unpack_from('<I', data, 0x3c)[0]
            require(data[pe:pe+4] == b'PE\0\0' and struct.unpack_from('<H', data, pe+4)[0] == 0x8664, 'Not Windows AMD64')
            require(struct.unpack_from('<H', data, pe+24+68)[0] == subsystem, 'Unexpected executable subsystem')
            env['LOCALAPPDATA'] = str(destination / (name + ' fresh user data'))
            target = destination / (name + ' synthetic workflow')
            run([str(exe), 'desktop-check', str(target)], name + '-workflow')
            case, workflow = validate_case(target)
            require(Path(workflow['module_location']).resolve().is_relative_to(bundle), 'Source-tree import detected')
            before = digest(case)
            # This launches a NEW OS process after the full GUI process exits.
            run([str(bundle / 'APM-cli.exe'), 'holmes', 'verify', str(case), '--expected-tip', workflow['integrity']['tip']], name + '-process-reopen')
            reopened = json.loads((destination / (name + '-process-reopen.txt')).read_text())
            require(reopened['tip'] == workflow['integrity']['tip'] and reopened['status'] == 'VERIFIED' and reopened['entries'] == 4, 'Independent process reopening failed')
            require(digest(case) == before, 'Reopening changed the journal database')
        require(digest(archive) == expected and digest(manifest_path) == result['manifest_sha256'], 'Qualification input changed')
        require(all(digest(destination / 'portable application' / name) == f['sha256'] for name, f in files.items()), 'Extracted application changed')
        result.update(status='PASS', native_widget_workflow='PASS', independent_process_reopen='PASS',
                      source_capsules_unchanged=True, original_archive_unchanged=True, evidence_authority='NONE')
    except Exception as exc:
        # Do not echo imported text or absolute private paths into a summary.
        result.update(status='FAIL', error_type=type(exc).__name__)
        if isinstance(exc, ValueError): result['reason'] = str(exc)
    finally:
        (destination / 'qualification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        lines = ['APM portable qualification: ' + result['status'], result['scope'],
                 'Clean machine: UNVERIFIED. Human visual acceptance: UNVERIFIED.',
                 'Installer, upgrade and uninstall: UNVERIFIED.',
                 'SHA-256 checks establish content consistency, not publisher authenticity.',
                 'Fixtures and process logs are retained in this qualification directory.', '', json.dumps(result, indent=2)]
        (destination / 'qualification.txt').write_text('\n'.join(lines), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--execute-reviewed-build', action='store_true')
    args = parser.parse_args()
    result = qualify(args.archive, args.sha256, args.manifest, args.destination, execute=args.execute_reviewed_build)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
