"""Publish only bounded synthetic CI diagnostics, never an archive or database."""
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
ALLOW=['cache/ci-lifecycle/lifecycle-summary.json',
       'cache/ci-lifecycle/lifecycle-1.txt','cache/ci-lifecycle/lifecycle-2.txt','cache/ci-lifecycle/lifecycle-3.txt',
       'cache/ci-tests/summary.json','cache/ci-tests/standard-1.txt',
       'cache/ci-package/qualification.json','cache/ci-package/qualification.txt',
       'cache/ci-components.json','cache/ci-build/freezer.txt','cache/ci-build/wheel.txt']

def collect(root=ROOT):
    target=root/'cache/ci-public';target.mkdir(parents=True,exist_ok=False)
    for name in ALLOW:
        source=root/name
        if not source.is_file() or source.is_symlink():continue
        if source.stat().st_size>2*1024*1024:
            (target/(source.name+'.omitted.txt')).write_text('Diagnostic exceeds 2 MiB; omitted, not passed.',encoding='utf-8')
        else:shutil.copyfile(source,target/source.name)
    return target

if __name__=='__main__':collect()
