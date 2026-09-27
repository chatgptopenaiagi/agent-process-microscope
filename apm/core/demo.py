"""Illustrative synthetic data only. This never touches a workspace."""
DEMO_EVENTS = [
    ('process', 'START', 'codex.exe', {'pid': 4242, 'parent_pid': 1000}),
    ('file', 'READ', 'src/engine.py', {'note': 'Synthetic read; live polling cannot observe reads.'}),
    ('file', 'WRITE', 'src/engine.py', {'added': 14, 'removed': 3}),
    ('command', 'EXECUTE', 'python -m pytest tests/', {'pid': 4243, 'cmdline': ['python', '-m', 'pytest', 'tests/']}),
    ('test', 'FAIL', 'pytest', {'passed': 4, 'failed': 1, 'exit_code': 1, 'duration_seconds': 1.8}),
    ('process', 'STOP', 'python.exe', {'pid': 4243, 'exit_code': 1}),
    ('file', 'WRITE', 'tests/test_engine.py', {'added': 3, 'removed': 1}),
    ('command', 'EXECUTE', 'python -m pytest tests/', {'pid': 4244, 'cmdline': ['python', '-m', 'pytest', 'tests/']}),
    ('test', 'PASS', 'pytest', {'passed': 5, 'failed': 0, 'exit_code': 0, 'duration_seconds': 1.2}),
    ('process', 'STOP', 'python.exe', {'pid': 4244, 'exit_code': 0}),
    ('git', 'SNAPSHOT', 'workspace', {'modified_files': 2, 'note': 'Synthetic diff summary'}),
    ('verification', 'VERIFY', 'Repository check complete', {'result': 'synthetic pass'}),
]


def demo_payloads():
    for category, action, target, metadata in DEMO_EVENTS:
        yield dict(source='synthetic-demo', category=category, action=action, target=target,
                   status='synthetic', confidence=1.0, interpretation_level='synthetic', metadata=metadata)
