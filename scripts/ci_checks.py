"""Bounded standard test runs with machine-readable measurements; no monkeypatch."""
import argparse
import json
import os
import platform
import re
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def inspect_test_log(value, expected_tests=None):
    """A zero exit code does not excuse unraisable Tcl/Tk shutdown errors."""
    markers = ('main thread is not in main loop', 'Tcl_AsyncDelete',
               'Tcl interpreter is leaked', 'Exception ignored', 'invalid command name')
    diagnostics = [marker for marker in markers if marker in value]
    if expected_tests is not None and (type(expected_tests) is not int or expected_tests < 1):
        raise ValueError('Expected test count must be a positive integer')
    counts = list(re.finditer(r'^Ran (\d+) tests? in (\d+(?:\.\d+)?)s\s*$', value, re.MULTILINE))
    count = counts[0] if len(counts) == 1 else None
    complete = bool(count and re.fullmatch(r'\s*OK\s*', value[count.end():]))
    count_matches = bool(count and int(count[1]) > 0 and
                         (expected_tests is None or int(count[1]) == expected_tests))
    return dict(test_count=int(count[1]) if count else None,
                unittest_seconds=float(count[2]) if count else None,
                shutdown_diagnostics=diagnostics,
                expected_test_count=expected_tests,
                unittest_ok=complete and count_matches)


def run(destination, repeat=1, expected_tests=None):
    if not 1 <= repeat <= 5: raise ValueError('Repeat bound is 1..5')
    destination = Path(destination).resolve()
    if not destination.is_relative_to(ROOT / 'cache'): raise ValueError('Use a new project cache destination')
    destination.mkdir(parents=True, exist_ok=False)
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
            text=True, timeout=10, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).strip()
    except (OSError, subprocess.SubprocessError):
        commit = None
    results = []
    for n in range(repeat):
        start = time.monotonic(); peak = 0; timed_out = False; unavailable = 0
        import psutil
        with (destination / ('standard-' + str(n + 1) + '.txt')).open('xb') as log:
            p = subprocess.Popen([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            observer = psutil.Process(p.pid)
            while p.poll() is None:
                try:
                    owned = [observer, *observer.children(recursive=True)[:64]]
                    total = 0
                    for process in owned:
                        try: total += process.memory_info().rss
                        except (psutil.NoSuchProcess, psutil.AccessDenied): unavailable += 1
                    peak = max(peak, total)
                except (psutil.NoSuchProcess, psutil.AccessDenied): unavailable += 1
                if time.monotonic() - start > 600:
                    timed_out = True; p.kill(); break
                time.sleep(.1)
            code = p.wait(timeout=10)
        diagnostics = inspect_test_log((destination / ('standard-' + str(n + 1) + '.txt')).read_text(encoding='utf-8', errors='replace'), expected_tests)
        results.append(dict(run=n + 1, exit_code=code, timeout=timed_out, **diagnostics,
                            seconds=round(time.monotonic() - start, 3), peak_owned_tree_rss_sampled_bytes=peak,
                            resource_unavailable_samples=unavailable))
        def passed(r):
            return r['exit_code'] == 0 and not r['timeout'] and r['unittest_ok'] and not r['shutdown_diagnostics']
        successful = all(passed(r) for r in results)
        status = 'FAIL' if not successful else ('PASS' if len(results) == repeat else 'PENDING')
        report = dict(status=status,
                      source_commit=commit, python=sys.version, platform=platform.platform(),
                      execution_context='GitHub Actions' if os.environ.get('GITHUB_ACTIONS')=='true' else 'Local invocation; token/owner identity not authenticated',
                      command='python -m unittest discover -s tests -v', runs=results,
                      completed_runs=len(results), requested_runs=repeat,
                      pass_rate=sum(passed(r) for r in results)/len(results),
                      resource_scope='Sum of launched process and up to 64 descendants RSS sampled at 100ms; shared pages may be counted repeatedly; not an exact peak',
                      ordinary_owner_token='Not inferred from this result')
        (destination / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--expected-tests', type=int)
    args=parser.parse_args()
    report=run(args.destination,args.repeat,args.expected_tests)
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['status']=='PASS' else 1)
