# One inspected application folder with GUI and console entry points.
from pathlib import Path

source = Path(SPECPATH)
a = Analysis([str(source / 'entry.py')], pathex=[str(source)], binaries=[],
             datas=[(str(source / 'LICENSE'), '.'), (str(source / 'NOTICE'), '.')],
             hiddenimports=[], hookspath=[], runtime_hooks=[],
             excludes=['pip', 'setuptools', 'unittest', 'test'], noarchive=False)
pyz = PYZ(a.pure)
gui = EXE(pyz, a.scripts, [], exclude_binaries=True, name='APM',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, version=str(source / 'version.txt'))
cli = EXE(pyz, a.scripts, [], exclude_binaries=True, name='APM-cli',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=True, version=str(source / 'version.txt'))
coll = COLLECT(gui, cli, a.binaries, a.datas, strip=False, upx=False, name='APM')
