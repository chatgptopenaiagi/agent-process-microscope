"""Small explicit CLI. Launching agents is an extension point, not a Genesis mode."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from uuid import uuid4

from apm.core.events import Normalizer, utc_now
from apm.core.state import StateEngine
from apm.storage.reader import read_session
from apm.storage.recorder import Recorder

DEFAULT_SESSIONS = Path(__file__).resolve().parent.parent / 'sessions'


def parser():
    result = argparse.ArgumentParser(prog='apm', description='Agent Process Microscope — external evidence, never private reasoning')
    result.add_argument('--demo', action='store_true', help='Open the GUI with a clearly synthetic session')
    commands = result.add_subparsers(dest='command')
    start = commands.add_parser('start', help='Attach to a selected PID; stopping observation never kills it')
    start.add_argument('--workspace', type=Path, default=Path.cwd())
    start.add_argument('--pid', type=int, help='Existing root process PID (required outside demo mode)')
    start.add_argument('--sessions', type=Path, default=DEFAULT_SESSIONS)
    start.add_argument('--demo', action='store_true')
    start.add_argument('--headless', action='store_true')
    start.add_argument('--duration', type=float, default=60, help='Headless observation bound in seconds (1–3600)')
    for name in ('replay', 'inspect'):
        command = commands.add_parser(name, help='Read a recorded APM session without executing its actions')
        command.add_argument('session', type=Path)
    imported = commands.add_parser('import-codex', help='Import an explicitly selected codex exec --json file; excludes reasoning and messages')
    imported.add_argument('path', type=Path)
    imported.add_argument('--sessions', type=Path, default=DEFAULT_SESSIONS)
    return result


def import_codex(path, sessions):
    from apm.observers.codex import CodexAdapter
    session_id = str(uuid4())
    normalizer = Normalizer(session_id, 'codex-json-import')
    target = Path(sessions).resolve() / (utc_now().replace(':', '').replace('.', '') + '_' + session_id)
    info = dict(schema_version='1.0', session_id=session_id, agent='codex-json-import',
                mode='import', status='recording', started_at=utc_now(),
                timestamp_semantics='import observation time; source stream order retained',
                workspace=None, source_file=str(Path(path).resolve()))
    adapter = CodexAdapter(Path(path))
    recorder = Recorder(target, info)
    state = StateEngine()
    outcome = 'stopped'
    try:
        while not adapter.done:
            for payload in adapter.poll():
                event = normalizer.normalize(payload)
                recorder.record(event)
                derived = state.accept(event)
                if derived:
                    recorder.record_state(derived)
        if adapter.counters['unavailable']:
            outcome = 'partial'
        if recorder.count == 0:
            outcome = 'empty'
    except Exception:
        outcome = 'error'
        raise
    finally:
        adapter.close()
        recorder.close(dict(status=outcome, stopped_at=utc_now(), counters=adapter.counters))
    print(f'Codex import {outcome}: {target}; counters: {adapter.counters}')
    return 0 if outcome == 'stopped' else 2


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == 'inspect':
            info, events, warnings = read_session(args.session)
            print(json.dumps(dict(session=info, recovered_events=len(events), warnings=warnings), indent=2))
            return 0
        if args.command == 'import-codex':
            return import_codex(args.path, args.sessions)
        if args.command == 'replay':
            from apm.ui.main_window import run_gui
            run_gui(session=args.session)
            return 0
        if args.command == 'start' and args.headless:
            from apm.core.controller import Controller
            if not 1 <= args.duration <= 3600:
                raise ValueError('Headless duration must be 1–3600 seconds')
            controller = Controller(args.workspace, args.sessions, args.pid, args.demo)
            print('DEMO / SYNTHETIC' if args.demo else f'OBSERVATION ACTIVE — PID {args.pid}; workspace {args.workspace}')
            controller.start()
            deadline = time.monotonic() + args.duration
            try:
                while time.monotonic() < deadline and controller.status not in ('stopped', 'error'):
                    for event in controller.drain():
                        print(f'{event.timestamp} {event.category.upper():10} {event.action:8} {event.target} [{event.status}]')
                    time.sleep(.1)
            except KeyboardInterrupt:
                pass
            finally:
                controller.stop()
                if not controller.wait(20):
                    raise RuntimeError('Observer has not stopped within its shutdown bound')
            print(f'Session: {controller.session_path}; status: {controller.status}; drops: {controller.dropped_count}')
            if controller.error:
                print(controller.error, file=sys.stderr)
                return 1
            return 0
        from apm.ui.main_window import run_gui
        run_gui(workspace=getattr(args, 'workspace', None), sessions_root=getattr(args, 'sessions', DEFAULT_SESSIONS),
                pid=getattr(args, 'pid', None), demo=args.demo)
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        from apm.security.redaction import redact_text
        print('APM: ' + redact_text(str(exc)), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
