"""Copy explicitly pinned, installed distributions into a NEW local build venv.

Offline fallback for restricted networking. Does not modify installed tools.
Local RECORD hashes are checked, but are not upstream signatures or provenance.
No global site-packages are enabled in the resulting environment.
"""
import argparse
import base64
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import shutil
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def prepare(destination, tools_site, runtime_site):
    destination = Path(destination).resolve()
    if not destination.is_relative_to(ROOT / 'cache') or destination.exists():
        raise ValueError('Choose a NEW build environment inside project cache')
    sources = [Path(tools_site).resolve(), Path(runtime_site).resolve()]
    requirements = (ROOT / 'packaging/build-requirements.txt').read_text().splitlines()
    selected = []
    for line in requirements:
        if not line.strip() or line.startswith('#'): continue
        name, version = line.strip().split('==')
        base = sources[1 if name == 'psutil' else 0]
        found = [d for d in metadata.distributions(path=[str(base)])
                 if d.metadata['Name'].lower().replace('_', '-') == name]
        if len(found) != 1 or found[0].version != version:
            raise ValueError('Pinned installed distribution unavailable: ' + name)
        selected.append((name, version, base, found[0]))
    venv.EnvBuilder(with_pip=False, clear=False).create(destination)
    site = destination / ('Lib/site-packages' if sys.platform == 'win32' else f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages')
    inventory = []
    for name, version, base, distribution in selected:
        files = []
        for relative in distribution.files or []:
            source = Path(distribution.locate_file(relative)).resolve()
            if not source.is_relative_to(base) or '__pycache__' in source.parts or source.suffix == '.pyc':
                continue  # Installed console launchers outside site-packages are unnecessary.
            data = source.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if relative.hash and relative.hash.mode == 'sha256':
                if base64.urlsafe_b64encode(bytes.fromhex(digest)).decode().rstrip('=') != relative.hash.value:
                    raise ValueError('Installed RECORD mismatch: ' + name)
            target = site / source.relative_to(base)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists(): raise ValueError('Distribution collision')
            with target.open('xb') as out: out.write(data)
            files.append(dict(path=source.relative_to(base).as_posix(), sha256=digest, bytes=len(data)))
        inventory.append(dict(name=name, version=version,
            license=distribution.metadata.get('License-Expression') or distribution.metadata.get('License'), files=files))
    (destination / 'offline-toolchain.json').write_text(json.dumps(dict(
        provenance='Explicit installed distributions; local RECORD checked, upstream authenticity unverified',
        python=sys.version, distributions=inventory), indent=2), encoding='utf-8')
    print(json.dumps(dict(environment=str(destination), distributions=len(inventory), status='COPIED_AND_RECORD_CHECKED')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    parser.add_argument('--tools-site', type=Path, required=True)
    parser.add_argument('--runtime-site', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.destination, args.tools_site, args.runtime_site)
