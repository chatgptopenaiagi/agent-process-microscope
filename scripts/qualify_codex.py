"""Owner-authorized, bounded qualification of the protected Codex public stream.

This is a test harness, never an observer execution API. It uses existing auth
without reading it, and never retries with relaxed security or another engine.
Raw stdout goes directly to the allowlisting companion. Startup diagnostics are
reduced in memory to fixed labels; raw stderr is never queued or recorded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
from uuid import uuid4

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from apm.core.controller import Controller
from apm.observatory.client import Outbox
from apm.observatory.transport import Receiver
from apm.storage.memory import Memory

ENGINE = Path(r'C:\Program Files\OpenAI\Codex\0.156.0-alpha.17\codex.exe')
HIDDEN = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def diagnostic_labels(raw):
    """Fixed operational labels only: no source text, paths or exception bodies."""
    lowered = raw.lower()
    patterns = {
        'access_denied': (b'access is denied', b'permission denied', b'os error 5'),
        'configuration_load_failed': (b'error loading config', b'failed to load config',
                                      b'error: reading config', b'error reading config'),
        'runtime_alias_creation_failed': (b'could not create path aliases',),
        'authentication_required': (b'not logged in', b'authentication required'),
        'connection_failed': (b'error sending request', b'connection refused'),
    }
    return {name for name, needles in patterns.items() if any(n in lowered for n in needles)}


def consume_diagnostics(stream, labels):
    # Bounded memory, drained concurrently to avoid blocking the owned process.
    # Keep overlap for split phrases, but never return or persist raw bytes.
    tail = b''
    try:
        while chunk := stream.read(4096):
            raw = tail + chunk
            labels.update(diagnostic_labels(raw))
            tail = raw[-128:]
    finally:
        stream.close()


def all_events(memory, session):
    rows, cursor = [], 0
    while True:
        page = memory.events(session, after=cursor)
        if not page:
            return rows
        rows.extend(page)
        cursor = page[-1]['arrival']


def evidence_checks(rows):
    """Report evidence predicates, never infer authentication from an error/exit."""
    reports = [r for r in rows if r['origin'] == 'reporter'
               and r['evidence_class'] == 'AGENT_REPORTED'
               and r['event']['source'] == 'codex']
    failures = [r['event']['event_id'] for r in reports
                if r['event']['category'] == 'command'
                and 'test_authorized.py' in r['event'].get('target', '')
                and r['event']['metadata'].get('codex_event') == 'item.completed'
                and type(r['event']['metadata'].get('exit_code')) is int
                and r['event']['metadata']['exit_code'] != 0]
    processes = [r for r in rows if r['origin'] == 'host'
                 and r['evidence_class'] == 'OBSERVED'
                 and r['event']['category'] == 'process'
                 and r['event']['metadata'].get('create_time') is not None]
    return dict(public_reports=len(reports), command_failure_ids=failures,
                turn_completed=any(r['event']['metadata'].get('codex_event') == 'turn.completed'
                                   for r in reports),
                process_generation_records=len(processes),
                child_generation_records=sum(r['event']['metadata'].get('pid') !=
                                             r['event']['metadata'].get('root_pid') for r in processes))


def inspect_gui(database, session, failure_ids):
    """Exercise real native widgets against this run, including a persisted Ask."""
    import tkinter as tk
    from apm.ui.memory_window import MemoryWindow
    root = tk.Tk()
    root.withdraw()
    window = MemoryWindow(root, database)
    def pump():
        deadline = time.monotonic() + 10
        while window.busy and time.monotonic() < deadline:
            root.update()
            time.sleep(.02)
        if window.busy:
            raise RuntimeError('gui_query_timeout')
    try:
        pump()
        window.session.set(session)
        window.load_events(reset=True)
        pump()
        count = len(window.tree.get_children())
        if count:
            window.tree.selection_set(window.tree.get_children()[0])
            window.details()
        details = bool(window.text.get('1.0', 'end').strip())
        window.ask()
        pump()
        text = window.text.get('1.0', 'end')
        return dict(widget_inspection=True, visible_manual_inspection=False,
                    displayed_records=count, evidence_details=details,
                    ask_rendered='Local evidence review:' in text,
                    cited_failure=any(ref in text for ref in failure_ids))
    finally:
        window.close()


def remember_owned(specimen, generations):
    """Only root and verified descendants; no machine-wide process enumeration."""
    try:
        root = psutil.Process(specimen.pid)
        known = generations.get(specimen.pid)
        if known is not None and root.create_time() != known:
            return
        generations[root.pid] = root.create_time()
        for child in root.children(recursive=True):
            generations[child.pid] = child.create_time()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass


def cleanup_owned(generations):
    """Harness-owned generations only, called after host observation is stopped."""
    remaining = []
    for pid, born in reversed(list(generations.items())):
        try:
            process = psutil.Process(pid)
            if process.create_time() != born:
                continue
            process.terminate()
            remaining.append(process)
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            remaining.append(process)
    _, alive = psutil.wait_procs(remaining, timeout=5)
    return [dict(pid=p.pid, create_time=generations[p.pid]) for p in alive]


def qualify(seconds=45):
    if not 5 <= seconds <= 120:
        raise ValueError('duration must be 5..120 seconds')
    run = ROOT / 'reports' / ('codex-qualification-' + str(uuid4()))
    workspace = run / 'workspace'
    workspace.mkdir(parents=True)
    (workspace / 'test_authorized.py').write_text(
        'import time, unittest\n'
        'class AuthorizedFailure(unittest.TestCase):\n'
        ' def test_deliberate_failure(self):\n'
        '  time.sleep(3)\n'
        '  self.assertEqual(1, 2, "authorized APM qualification fixture")\n', encoding='utf8')
    (workspace / 'AGENTS.md').write_text(
        'This disposable workspace is authorized for one deliberately failing unittest.\n'
        'Run only the requested test. Do not fix it, install anything, read outside this\n'
        'workspace, use connectors, inspect credentials/history, or change configuration.\n', encoding='utf8')
    session, writer = str(uuid4()), secrets.token_hex(32)
    database, spool = run / 'memory.sqlite3', run / 'outbox.sqlite3'
    cap = run / 'reporter.key'
    cap.write_text(json.dumps(dict(credential=writer, session_id=session)), encoding='utf8')
    report = dict(session_id=session, database=str(database), workspace=str(workspace),
                  engine=str(ENGINE), authenticated_workflow='UNVERIFIED',
                  raw_stdout_retained=False, raw_stderr_retained=False,
                  auth_or_configuration_inspected=False, timed_out=False, errors=[])
    specimen = companion = controller = worker = diagnostics = None
    labels = set()
    generations = {}
    digest = hashlib.sha256(ENGINE.read_bytes()).hexdigest()
    report['engine_sha256_before'] = digest
    print(f'Qualification artifacts: {run}', flush=True)
    with Memory(database) as memory, Receiver(memory, {writer: dict(role='reporter', session_id=session)}, 0) as server:
        port = server.server_address[1]
        worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .05})
        worker.start()
        try:
            # Inherit the engine's existing auth/config route. No login, copying,
            # config override, alternate home, rule bypass or sandbox relaxation.
            specimen = subprocess.Popen([str(ENGINE), '-a', 'never', 'exec', '--json',
                '--ephemeral', '--sandbox', 'read-only', '--skip-git-repo-check',
                '-C', str(workspace), '-'], cwd=workspace, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=HIDDEN)
            diagnostics = threading.Thread(target=consume_diagnostics,
                args=(specimen.stderr, labels), name='APM startup diagnostic filter', daemon=True)
            diagnostics.start()
            remember_owned(specimen, generations)
            companion = subprocess.Popen([sys.executable, '-m', 'apm', 'feed-codex',
                '--capability', str(cap), '--outbox', str(spool), '--port', str(port)],
                cwd=ROOT, stdin=specimen.stdout, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, creationflags=HIDDEN)
            specimen.stdout.close()
            controller = Controller(workspace, run / 'sessions', specimen.pid,
                                    memory_path=database, session_id=session)
            controller.start()
            # Let independent collection attach before releasing the prompt.
            time.sleep(.3)
            prompt = (f'Run exactly this one engineering check in the current disposable workspace. '
                      f'Execute this PowerShell command verbatim:\n'
                      f'& "{sys.executable}" -B -m unittest test_authorized.py\n'
                      'The test intentionally fails. Do not repair it or run other commands. '
                      'Do not inspect credentials, histories, configuration or other directories. '
                      'After the command returns, give only a brief completion message.')
            try:
                specimen.stdin.write(prompt.encode('utf8'))
                specimen.stdin.close()
            except (BrokenPipeError, OSError):
                report['errors'].append('engine_closed_prompt_pipe')
            deadline = time.monotonic() + seconds
            while specimen.poll() is None and time.monotonic() < deadline:
                remember_owned(specimen, generations)
                time.sleep(.1)
            report['timed_out'] = specimen.poll() is None
            report['engine_exit_before_cleanup'] = specimen.poll()
        except (OSError, ValueError, RuntimeError) as exc:
            report['errors'].append(type(exc).__name__)
        finally:
            if controller:
                controller.stop()
                report['observer_stopped'] = controller.wait(20)
                report['observer_status'] = controller.status
            report['alive_at_observer_stop'] = bool(specimen and specimen.poll() is None)
            # This runner owns the probe. Controller.stop never terminates it.
            report['owned_generations_remaining'] = cleanup_owned(generations)
            if specimen:
                try:
                    specimen.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    report['errors'].append('engine_cleanup_timeout')
                if specimen.stdin and not specimen.stdin.closed:
                    specimen.stdin.close()
            if companion:
                try:
                    report['companion_exit'] = companion.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    companion.terminate()
                    companion.wait(timeout=5)
                    report['errors'].append('companion_cleanup_timeout')
            if diagnostics:
                diagnostics.join(5)
                report['diagnostic_reader_finished'] = not diagnostics.is_alive()
                report['startup_diagnostic_labels'] = sorted(labels)
            server.shutdown()
            worker.join(5)
            report['receiver_health'] = server.health.copy()
    # Receiver has stopped; a fresh CLI process verifies actual restart recovery.
    recovered = subprocess.run([sys.executable, '-m', 'apm', 'memory', str(database),
        '--operation', 'verify'], cwd=ROOT, capture_output=True, timeout=15, creationflags=HIDDEN)
    report['restart_verify_exit'] = recovered.returncode
    report['restart_integrity'] = json.loads(recovered.stdout) if recovered.returncode == 0 else None
    if spool.exists():
        outbox = Outbox(spool)
        try:
            report['pending_after_restart'] = outbox.pending
        finally:
            outbox.close()
    with Memory(database) as reopened:
        rows = all_events(reopened, session)
        report['checks'] = evidence_checks(rows)
        result = reopened.investigate(session)
        report['investigation'] = result
        reopened.save_investigation(result)
    try:
        report['gui'] = inspect_gui(database, session, report['checks']['command_failure_ids'])
    except Exception as exc:
        report['gui'] = dict(widget_inspection=False, error=type(exc).__name__)
    with Memory(database, readonly=True) as reopened:
        report['final_integrity'] = reopened.verify()
    report['engine_sha256_unchanged'] = hashlib.sha256(ENGINE.read_bytes()).hexdigest() == digest
    report['owned_generations'] = [dict(pid=pid, create_time=born) for pid, born in generations.items()]
    # Even a completed turn alone is insufficient to qualify the engineering run.
    report['engineering_evidence_complete'] = bool(
        report['checks']['command_failure_ids'] and report['checks']['turn_completed']
        and report['checks']['child_generation_records'] and report.get('companion_exit') == 0
        and report.get('pending_after_restart') == 0 and report['final_integrity']['ok']
        and report['restart_verify_exit'] == 0 and report.get('observer_stopped')
        and report.get('observer_status') == 'stopped' and not report['errors']
        and not report['timed_out'] and not report['owned_generations_remaining']
        and report['engine_sha256_unchanged'] and report.get('diagnostic_reader_finished')
        and report['gui'].get('cited_failure'))
    report['limits'] = ('Public reports do not attest account identity; credentials were not inspected. '
                        'PID ancestry and receipt timing do not prove command attribution. '
                        'GUI checks exercise withdrawn native widgets, not human visual approval. '
                        'No bidirectional human-AI communication claim. Raw failure causes are excluded.')
    (run / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps({k: v for k, v in report.items() if k != 'investigation'}, indent=2))
    return 0 if report['engineering_evidence_complete'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=int, default=45)
    args = parser.parse_args()
    raise SystemExit(qualify(args.seconds))
