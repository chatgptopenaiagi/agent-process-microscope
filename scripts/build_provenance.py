"""Local hash-pinned build inputs and deterministic ZIP serialization.

Local hashes detect drift; they do not authenticate upstream publishers. No
downloads or installation. A lock must be explicitly generated and reviewed.
"""
import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import sys
import time
import zipfile


def digest(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()


def installed_inventory(requirements):
    distributions = []
    for line in Path(requirements).read_text().splitlines():
        if not line.strip() or line.startswith('#'): continue
        name, version = line.strip().split('==')
        dist = metadata.distribution(name)
        if dist.version != version: raise ValueError('Build version mismatch: ' + name)
        files = []
        for relative in dist.files or []:
            p = Path(relative)
            # Ignore generated scripts and interpreter-specific caches only.
            if '..' in p.parts or '__pycache__' in p.parts or p.suffix == '.pyc': continue
            target = Path(dist.locate_file(relative))
            if not target.is_file() or target.is_symlink(): raise ValueError('Missing or linked distribution input')
            files.append(dict(path=p.as_posix(), sha256=digest(target)))
        if not files: raise ValueError('No recorded distribution inputs')
        encoded = json.dumps(sorted(files, key=lambda f:f['path']), sort_keys=True, separators=(',', ':')).encode()
        distributions.append(dict(name=name, version=version, files=len(files),
                                  inventory_sha256=hashlib.sha256(encoded).hexdigest()))
    base = Path(sys.base_prefix)
    runtime = []
    # Include the actual Python/Tk/stdlib input tree, excluding installed packages,
    # caches and development tools. Hashes use relative paths, never user paths.
    inputs = [*base.glob('python*.exe'), *base.glob('python*.dll'), base / 'LICENSE.txt']
    for directory in ('DLLs', 'tcl', 'Lib'):
        for p in (base / directory).rglob('*'):
            rel = p.relative_to(base)
            if any(part in ('site-packages', '__pycache__') for part in rel.parts) or p.suffix == '.pyc': continue
            if p.is_file(): inputs.append(p)
    for p in sorted(set(inputs)):
        if p.is_symlink(): raise ValueError('Linked runtime input')
        runtime.append(dict(path=p.relative_to(base).as_posix(), sha256=digest(p)))
    return dict(schema_version=1, python=sys.version, distributions=distributions,
                python_runtime_files=len(runtime),
                python_runtime_inventory_sha256=hashlib.sha256(json.dumps(runtime, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                provenance='Local installed files only; upstream authenticity and clean-environment reconstruction UNVERIFIED')


def verify_lock(requirements, lock):
    expected = json.loads(Path(lock).read_text())
    actual = installed_inventory(requirements)
    if actual != expected: raise ValueError('Build input hash lock mismatch; investigate instead of silently refreshing')
    return actual


def deterministic_zip(bundle, destination, epoch):
    """Stable member order, timestamps and attributes; no bitwise-build claim."""
    stamp = time.gmtime(epoch)[:6]
    if not 1980 <= stamp[0] <= 2107: raise ValueError('ZIP epoch outside supported range')
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(Path(bundle).rglob('*')):
            if p.is_symlink(): raise ValueError('Linked bundle input')
            if not p.is_file(): continue
            item = zipfile.ZipInfo('APM/' + p.relative_to(bundle).as_posix(), stamp)
            item.create_system = 3; item.external_attr = 0o100644 << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(item, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--requirements', type=Path, required=True)
    parser.add_argument('--write-new-lock', type=Path)
    parser.add_argument('--verify-lock', type=Path)
    args = parser.parse_args()
    if args.write_new_lock:
        result = installed_inventory(args.requirements)
        with args.write_new_lock.open('x', encoding='utf-8') as f: json.dump(result, f, indent=2)
    elif args.verify_lock:
        result = verify_lock(args.requirements, args.verify_lock)
    else: parser.error('Choose an explicit new lock or verification')
    print(json.dumps(dict(status='PASS', distributions=len(result['distributions']), python_runtime_files=result['python_runtime_files'])))
