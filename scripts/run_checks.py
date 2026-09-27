"""Run the bounded Genesis test suite and keep inspectable local results."""
import json
from pathlib import Path
import sys
import time
import unittest

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
reports = root / 'reports'
reports.mkdir(exist_ok=True)
started = time.time()
suite = unittest.defaultTestLoader.discover(str(root / 'tests'))
with (reports / 'tests.log').open('w', encoding='utf-8') as log:
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
summary = {'status': 'passed' if result.wasSuccessful() else 'failed',
           'tests': result.testsRun, 'failures': len(result.failures),
           'errors': len(result.errors), 'skipped': len(result.skipped),
           'duration_seconds': round(time.time() - started, 3),
           'python': sys.version, 'log': str(reports / 'tests.log')}
(reports / 'test-results.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
raise SystemExit(not result.wasSuccessful())
