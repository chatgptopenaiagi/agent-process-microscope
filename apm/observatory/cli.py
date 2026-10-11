"""Explicit local capabilities; no discovery of private histories or credentials."""
from __future__ import annotations

import json
from pathlib import Path
import secrets
import sqlite3
import sys
import threading
import time
from uuid import uuid4

from apm.core.events import Normalizer
from apm.storage.memory import Memory, explanation
from .transport import Receiver, request
from .client import Outbox


def add_commands(commands):
    init = commands.add_parser('memory-init', help='Create session-scoped capability files in a NEW local directory')
    init.add_argument('directory', type=Path)
    serve = commands.add_parser('serve', help='Bounded local receiver; optional explicit host observation')
    serve.add_argument('--config', type=Path, required=True)
    serve.add_argument('--database', type=Path, required=True)
    serve.add_argument('--port', type=int, default=47631)
    serve.add_argument('--duration', type=float, default=3600)
    serve.add_argument('--pid', type=int)
    serve.add_argument('--workspace', type=Path)
    serve.add_argument('--sessions', type=Path, default=Path('sessions'))
    feed = commands.add_parser('feed-codex', help='Read public exec JSONL from stdin, sanitize, spool, send')
    feed.add_argument('--capability', type=Path, required=True)
    feed.add_argument('--outbox', type=Path, required=True)
    feed.add_argument('--port', type=int, default=47631)
    feed.add_argument('--retry-only', action='store_true', help='Retry retained outbox without reading stdin')
    query = commands.add_parser('query', help='Session-scoped read-only access for an authorized investigator')
    query.add_argument('--capability', type=Path, required=True)
    query.add_argument('--port', type=int, default=47631)
    query.add_argument('--operation', choices=('events', 'investigate', 'health'), default='investigate')
    query.add_argument('--after', type=int, default=0)
    query.add_argument('--search', default='')
    memory = commands.add_parser('memory', help='SQL history, investigation, integrity, backup and human notes')
    memory.add_argument('database', type=Path)
    memory.add_argument('--session')
    memory.add_argument('--operation', choices=('sessions', 'events', 'ask', 'verify', 'backup', 'note', 'gui', 'review'), default='sessions')
    memory.add_argument('--after', type=int, default=0)
    memory.add_argument('--search', default='')
    memory.add_argument('--destination', type=Path)
    memory.add_argument('--text')
    memory.add_argument('--decision', choices=('annotate', 'approve', 'reject', 'investigate', 'correct'), default='annotate')
    memory.add_argument('--reference', action='append', default=[])
    memory.add_argument('--expected-tip')


def read_config(path):
    if path.stat().st_size > 16384:
        raise ValueError('configuration_size')
    return json.loads(path.read_text(encoding='utf8'))


def run_command(args):
    if args.command not in ('memory-init', 'serve', 'feed-codex', 'query', 'memory'):
        return None
    try:
        return _run(args)
    except (sqlite3.Error, KeyError, TypeError):
        raise ValueError('Memory operation unavailable; check database, capability format and local storage.') from None


def _run(args):
    if args.command == 'memory-init':
        args.directory.mkdir(parents=True, exist_ok=False)
        session = str(uuid4())
        reporter, reader = secrets.token_hex(32), secrets.token_hex(32)
        grants = {reporter: {'role': 'reporter', 'session_id': session},
                  reader: {'role': 'reader', 'session_id': session}}
        for name, data in [('receiver.key', grants),
                           ('reporter.key', dict(credential=reporter, session_id=session)),
                           ('reader.key', dict(credential=reader, session_id=session))]:
            with (args.directory / name).open('x', encoding='utf8') as f:
                json.dump(data, f)
        print(f'Created local session {session}. Capability files inherit directory access; keep them private.')
        return 0
    if args.command == 'serve':
        if not 1 <= args.duration <= 3600 or not 1 <= args.port <= 65535:
            raise ValueError('Receiver duration must be 1–3600 seconds; port must be 1–65535.')
        if (args.pid is None) != (args.workspace is None):
            raise ValueError('Host observation needs both --pid and --workspace.')
        grants = read_config(args.config)
        controller = None
        with Memory(args.database) as memory, Receiver(memory, grants, args.port) as server:
            if args.pid is not None:
                scopes = {g['session_id'] for g in grants.values()}
                if len(scopes) != 1:
                    raise ValueError('Host observation requires one explicit session scope.')
                from apm.core.controller import Controller
                controller = Controller(args.workspace, args.sessions, args.pid,
                                        memory_path=args.database, session_id=next(iter(scopes)))
                controller.start()
            worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .1}, name='APM receiver')
            worker.start()
            print(f'Receiver protocol 1 listening on 127.0.0.1:{args.port}; duration {args.duration}s.', flush=True)
            deadline = time.monotonic() + args.duration
            try:
                while time.monotonic() < deadline:
                    if controller and controller.status == 'error':
                        raise RuntimeError('Host observer failed: ' + str(controller.error))
                    time.sleep(.1)
            except KeyboardInterrupt:
                pass
            finally:
                if controller:
                    controller.stop()
                    if not controller.wait(20):
                        print('Host observer shutdown incomplete.', file=sys.stderr)
                server.shutdown()
                worker.join(5)
            print(json.dumps(server.health))
        return 0
    if args.command == 'feed-codex':
        from .codex_stream import CodexStream
        cap = read_config(args.capability)
        normalizer = Normalizer(cap['session_id'], 'codex-exec-stream')
        outbox = Outbox(args.outbox)
        next_retry = 0
        try:
            if not args.retry_only:
                for payload in CodexStream().read(sys.stdin.buffer):
                    outbox.enqueue(normalizer.normalize(payload).to_dict())
                    if time.monotonic() >= next_retry:
                        try:
                            outbox.flush(args.port, cap['credential'])
                        except (OSError, ValueError):
                            next_retry = time.monotonic() + 2
            try:
                while outbox.pending:
                    outbox.flush(args.port, cap['credential'])
            except (OSError, ValueError):
                print(f'Receiver unavailable or rejected delivery; {outbox.pending} records retained. Use --retry-only.', file=sys.stderr)
                return 2
            print('All accepted source records acknowledged. Source completeness is not established.')
            return 0
        finally:
            outbox.close()
    if args.command == 'query':
        cap = read_config(args.capability)
        params = dict(after=args.after, search=args.search) if args.operation == 'events' else {}
        print(json.dumps(request(args.port, cap['credential'], args.operation, **params), indent=2))
        return 0
    if args.operation in ('gui', 'review'):
        import tkinter as tk
        from apm.ui.memory_window import MemoryWindow
        root = tk.Tk()
        if args.operation == 'review':
            from apm.ui.qualification_window import QualificationWindow
            QualificationWindow(root, args.database, session=args.session, expected_tip=args.expected_tip)
        else:
            MemoryWindow(root, args.database)
        root.mainloop()
        return 0
    with Memory(args.database, readonly=args.operation not in ('note', 'ask')) as memory:
        if args.operation == 'sessions':
            result = memory.sessions()
        elif args.operation == 'verify':
            result = memory.verify(args.expected_tip)
        elif args.operation == 'backup':
            if not args.destination:
                raise ValueError('--destination required')
            memory.backup(args.destination)
            result = {'backup': str(args.destination)}
        else:
            if not args.session:
                raise ValueError('--session required')
            if args.operation == 'events':
                result = memory.events(args.session, after=args.after, search=args.search)
            elif args.operation == 'note':
                result = memory.note(args.session, args.text, decision=args.decision, references=args.reference)
            else:
                result = memory.investigate(args.session)
                memory.save_investigation(result)
                print(explanation(result))
                return 0
        print(json.dumps(result, indent=2))
        return 1 if args.operation == 'verify' and not result['ok'] else 0
