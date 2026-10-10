"""Reproducible native failure slice. A controlled runner, NOT a Codex model run.

Starts a hidden fixture that genuinely fails unittest, observes its OS process,
sends its real exit report through the companion/receiver, reopens SQL, and asks.
All artifacts remain under ignored reports/; no external services are started.
"""
from pathlib import Path
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from apm.core.controller import Controller
from apm.core.events import Normalizer
from apm.observatory.client import Outbox
from apm.observatory.transport import Receiver, request
from apm.storage.memory import Memory, explanation


def main():
    run = ROOT / 'reports' / ('observatory-native-' + str(uuid4()))
    workspace = run / 'workspace'; workspace.mkdir(parents=True)
    # A selected, deliberately failing test fixture. Its failure really executes.
    (workspace / 'test_controlled.py').write_text(
        'import time, unittest\n'
        'class ControlledFailure(unittest.TestCase):\n'
        ' def test_expected_failure(self):\n'
        '  time.sleep(3)\n'
        '  self.assertEqual(1, 2, "deliberate observatory fixture")\n', encoding='utf8')
    session = str(uuid4())
    writer, reader = secrets.token_hex(32), secrets.token_hex(32)
    database = run / 'observatory.sqlite3'
    started = time.perf_counter()
    config = run / 'receiver.key'
    config.write_text(json.dumps({writer: {'role':'reporter','session_id':session},
                                 reader: {'role':'reader','session_id':session}}), encoding='utf8')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
    with (run / 'receiver.log').open('w', encoding='utf8') as log:
        specimen = subprocess.Popen([sys.executable, '-m', 'unittest', 'discover', '-s', str(workspace)],
                                    cwd=workspace, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        receiver = subprocess.Popen([sys.executable, '-m', 'apm', 'serve', '--config', str(config),
            '--database', str(database), '--port', str(port), '--duration', '6', '--pid', str(specimen.pid),
            '--workspace', str(workspace), '--sessions', str(run / 'sessions')],
            cwd=ROOT, stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        outbox = Outbox(run / 'companion.sqlite3')
        try:
            deadline = time.monotonic()+5
            while True:
                try:
                    request(port, reader, 'health'); break
                except (OSError, ValueError):
                    if time.monotonic() >= deadline or receiver.poll() is not None:
                        raise RuntimeError('Separate receiver did not become ready')
                    time.sleep(.05)
            code = specimen.wait(timeout=15)
            event = Normalizer(session, 'controlled-runner').normalize(dict(
                source='controlled-runner', category='command', action='STOP', target='python -m unittest (controlled failure fixture)',
                metadata={'exit_code': code, 'workload':'deliberately failing native fixture',
                          'provenance':'runner_observed_exit_report',
                          'pid':specimen.pid, 'attribution_limit':'Selected workload; not a Codex report or model run.'}))
            outbox.enqueue(event.to_dict())
            outbox.flush(port, writer)
            result = request(port, reader, 'investigate')
            assert any(f['evidence_id'] == event.event_id for f in result['findings'])
        finally:
            outbox.close()
            if specimen.poll() is None:
                # Own fixture only. Never terminate an attached external specimen.
                specimen.terminate(); specimen.wait(timeout=5)
            receiver.wait(timeout=20)
        assert receiver.returncode == 0, 'Receiver failed; inspect local receiver.log'
    with Memory(database) as recovered:
        events = recovered.events(session)
        assert any(r['origin']=='host' and r['event']['category']=='process' for r in events)
        assert any(r['origin']=='reporter' and r['event']['metadata'].get('exit_code')==1 for r in events)
        result = recovered.investigate(session)
        recovered.save_investigation(result)
        recovered.note(session, 'Confirmed: this is the deliberately failing validation workload.', references=[event.event_id])
        integrity = recovered.verify()
        assert integrity['ok']
        recovered.backup(run / 'backup.sqlite3')
    report = dict(label='REAL NATIVE OBSERVATIONS OF A CONTROLLED FAILURE FIXTURE; NOT A CODEX MODEL RUN',
                  session_id=session, database=str(database), recorded_events=len(events),
                  exit_code=code, receiver_exit_code=receiver.returncode, engines='separate OS processes', integrity=integrity,
                  elapsed_seconds=round(time.perf_counter()-started,3), explanation=explanation(result))
    (run / 'result.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
