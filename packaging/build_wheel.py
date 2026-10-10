"""Build-only backend launcher. Optional restricted-token accommodation is local.

No global ACL or Python configuration change. The flag uses inherited permissions
for new build temporary directories only; it is not a standard-command pass.
"""
import argparse
import os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('destination', type=Path)
parser.add_argument('--restricted-temp-compat', action='store_true')
args = parser.parse_args()
scope = Path(__file__).resolve().parent.parent
destination = args.destination.resolve()
if not destination.is_relative_to(scope): raise ValueError('Wheel destination outside isolated build')
if args.restricted_temp_compat:
    original = os.mkdir
    def mkdir(path, mode=0o777, *, dir_fd=None):
        if os.name == 'nt' and mode == 0o700 and Path(path).resolve().is_relative_to(scope): mode = 0o777
        return original(path, mode, dir_fd=dir_fd)
    os.mkdir = mkdir
import setuptools.build_meta as backend
backend.build_wheel(str(destination))
