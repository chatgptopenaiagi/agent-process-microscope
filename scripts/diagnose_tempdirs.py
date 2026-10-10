"""Reproduce Windows temporary-directory failures without changing any ACL.

No APM imports or monkeypatches. Creates only new, synthetic, ignored fixtures;
inaccessible fixtures are left in place. Never repairs permissions or elevates.
"""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import tempfile
from uuid import uuid4


def restricted_token():
    if os.name != 'nt':
        return None
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.IsTokenRestricted.argtypes = [wintypes.HANDLE]
    advapi.IsTokenRestricted.restype = wintypes.BOOL
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
        return 'unavailable'
    try:
        return bool(advapi.IsTokenRestricted(token))
    finally:
        kernel.CloseHandle(token)


def exercise(path, create):
    result = {}
    def attempt(name, action):
        try:
            action()
            result[name] = dict(ok=True)
            return True
        except OSError as exc:
            result[name] = dict(ok=False, error=type(exc).__name__,
                                errno=exc.errno, winerror=getattr(exc, 'winerror', None))
            return False
    if not attempt('create', create):
        return result
    marker = path / 'synthetic-marker.txt'
    attempt('write_child', lambda: marker.write_text('synthetic permission probe', encoding='ascii'))
    def scan():
        with os.scandir(path) as entries:
            list(entries)
    attempt('scan', scan)
    attempt('remove_child', lambda: marker.unlink(missing_ok=True))
    attempt('remove_directory', path.rmdir)
    return result


def main():
    root = Path(__file__).resolve().parents[1]
    run = root / 'reports' / ('tempdir-diagnostic-' + str(uuid4()))
    run.mkdir(parents=True)
    cases = {}
    for mode in (0o700, 0o777):
        path = run / f'mode-{mode:o}'
        cases[f'os.mkdir_{mode:o}'] = exercise(path, lambda: os.mkdir(path, mode))
    # tempfile selects an unpredictable basename; learn only our returned path.
    try:
        path = Path(tempfile.mkdtemp(prefix='stdlib-', dir=run))
        cases['tempfile.mkdtemp'] = exercise(path, lambda: None)
    except OSError as exc:
        cases['tempfile.mkdtemp'] = dict(create=dict(ok=False, error=type(exc).__name__,
            errno=exc.errno, winerror=getattr(exc, 'winerror', None)))
    report = dict(python=sys.version, restricted_token=restricted_token(),
                  apm_imported=False, acl_changes=False, cases=cases)
    (run / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(str(run / 'result.json'))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
