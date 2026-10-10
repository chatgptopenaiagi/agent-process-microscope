"""Explicit Windows sandbox test accommodation, never imported by APM.

Python 3.14 Windows mkdir(mode=0700) constructs a private ACL that can exclude
the restricted execution identity. Tests use inherited ACLs in THIS PROCESS,
only for directories inside the repository. No machine ACL/config is changed.
The original unmodified unittest command must also be recorded separately.
"""
import os
from pathlib import Path
import runpy
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
original_mkdir = os.mkdir


def test_mkdir(path, mode=0o777, *, dir_fd=None):
    if os.name == 'nt' and mode == 0o700 and Path(path).resolve().is_relative_to(root):
        mode = 0o777
    return original_mkdir(path, mode, dir_fd=dir_fd)


if __name__ == '__main__':
    test_temp = root / 'cache' / 'sandbox-test-temp'
    test_temp.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(test_temp)
    os.mkdir = test_mkdir
    sys.path.insert(0, str(root))
    sys.argv = ['unittest', 'discover', '-s', str(root / 'tests'), '-v']
    runpy.run_module('unittest', run_name='__main__')
