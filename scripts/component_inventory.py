"""Local component inventory, explicitly NOT a validated CycloneDX SBOM."""
import argparse
import importlib.metadata as metadata
import json
from pathlib import Path


def inventory(manifest):
    components=[]
    locked = {c['name']: c for c in manifest.get('toolchain', {}).get('distributions', [])}
    for name,version in manifest['build_dependencies'].items():
        dist=metadata.distribution(name)
        if dist.version != version: raise ValueError('Inventory toolchain version mismatch')
        license_name=dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'UNKNOWN'
        if len(license_name)>300: license_name='See retained license text; expression UNKNOWN'
        components.append(dict(name=name,version=version,
            relationship='direct runtime dependency' if name=='psutil' else 'build environment dependency',
            package_source='https://pypi.org/project/'+name+'/'+version+'/',
            source_verification='Installed distribution; upstream authenticity UNVERIFIED',
            license=license_name,declared_requires=list(dist.requires or []),
            distribution_status='Runtime included' if name=='psutil' else 'Build tooling; notices may be retained',
            hashes=([dict(algorithm='SHA-256',scope='local installed-file inventory',
                          value=locked[name]['inventory_sha256'])] if name in locked else [])))
    binaries=[]
    for f in manifest['bundle']:
        p=Path(f['path'])
        if p.suffix.lower() in ('.exe','.dll','.pyd'):
            if p.is_absolute() or '..' in p.parts: raise ValueError('Nonportable binary path')
            binaries.append(dict(name=p.name,relative_path=p.as_posix(),sha256=f['sha256'],
                version='UNKNOWN unless identified in component metadata',
                license='UNKNOWN: map this binary to retained upstream notices before release',
                authenticity='UNVERIFIED'))
    return dict(format='apm-local-component-inventory',schema_version=1,
        standards_compliance='NOT CycloneDX; no compliant generator/schema validation performed',
        application_version='0.2.0.dev1',python=manifest['python'],
        components=components,binary_inventory=binaries,
        runtime_components=[dict(name=n,version=v,license=l) for n,v,l in [
            ('Python',manifest['python'].split()[0],'PSF and bundled component notices'),
            ('Tcl/Tk','UNKNOWN patch version','Retained upstream permissive notices; binary mapping pending'),
            ('SQLite','UNKNOWN bundled version','Public domain declaration; binary mapping pending'),
            ('Microsoft runtime','UNKNOWN','Redistribution terms require review')]],
        unresolved=['Complete transitive DLL license/version mapping','Independent upstream artifact provenance',
                    'Supported Windows version matrix','Code signing and publisher identity'],
        legal_clearance='PENDING',private_paths_included=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.manifest.stat().st_size>2*1024*1024:raise ValueError('Manifest size')
    result=inventory(json.loads(a.manifest.read_text(encoding='utf-8')))
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
