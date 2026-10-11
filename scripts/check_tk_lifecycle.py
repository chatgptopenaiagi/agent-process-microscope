"""Repeat adjacent GUI tests in fresh processes and different orders; no skipped failures."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.ci_checks import inspect_test_log

TESTS = (
    'test_desktop.DesktopTests.test_permission_failure_has_explicit_outcome_without_private_error_text',
    'test_desktop.DesktopTests.test_rejected_capsule_preserves_case_and_source',
    'test_desktop.DesktopTests.test_demo_complete_workflow_close_reopen_and_report',
    'test_tk_ownership.TkOwnershipTests',
)


def run(destination, repeat=3):
    if not 1 <= repeat <= 10:
        raise ValueError('Repeat must be 1..10')
    destination = Path(destination).resolve()
    if not destination.is_relative_to(ROOT / 'cache'):
        raise ValueError('Use a new project cache directory')
    destination.mkdir(parents=True, exist_ok=False)
    runs = []
    for number in range(repeat):
        order = TESTS if number % 2 == 0 else tuple(reversed(TESTS))
        command = [sys.executable, str(Path(__file__).resolve()), '--child', *order]
        start = time.monotonic()
        with (destination / f'lifecycle-{number + 1}.txt').open('xb') as log:
            process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            timed_out = False
            try:
                code = process.wait(timeout=120)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill(); code = process.wait(timeout=10)
        data = inspect_test_log((destination / f'lifecycle-{number + 1}.txt').read_text(encoding='utf-8', errors='replace'))
        runs.append(dict(run=number + 1, order=order, exit_code=code, timeout=timed_out,
                         seconds=round(time.monotonic()-start, 3), **data))
    passed = all(r['exit_code'] == 0 and not r['timeout'] and r['unittest_ok'] and not r['shutdown_diagnostics'] for r in runs)
    report = dict(status='PASS' if passed else 'FAIL', python=sys.version,
                  platform=platform.platform(), runs=runs,
                  context='GitHub Actions' if os.environ.get('GITHUB_ACTIONS') == 'true' else 'Local development process')
    (destination / 'lifecycle-summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--child':
        import unittest
        sys.path.insert(0, str(ROOT / 'tests'))
        unittest.main(module=None, argv=[sys.argv[0], '-v', *sys.argv[2:]])
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--destination', type=Path, required=True)
        parser.add_argument('--repeat', type=int, default=3)
        args = parser.parse_args()
        result = run(args.destination, args.repeat)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result['status'] == 'PASS' else 1)
