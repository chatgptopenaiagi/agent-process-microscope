from __future__ import annotations

import os
import platform
from pathlib import Path
from queue import Queue, Empty, Full
import threading
import time
from uuid import uuid4

from apm.core.bus import EventBus
from apm.core.demo import demo_payloads
from apm.core.events import Normalizer, utc_now
from apm.core.state import StateEngine
from apm.security.redaction import redact_text, sanitize
from apm.storage.recorder import Recorder


class Controller:
    """One collection worker, bounded queues, flush/checkpoint and explicit scope."""
    def __init__(self, workspace, sessions_root, pid=None, demo=False):
        self.workspace = Path(os.path.abspath(workspace))
        self.sessions_root = Path(sessions_root).resolve()
        if not self.workspace.is_dir():
            raise ValueError('Workspace must be an existing directory')
        if not demo and (pid is None or int(pid) <= 0):
            raise ValueError('Attach mode requires a positive root process PID')
        self.pid, self.demo = pid, demo
        session_id = str(uuid4())
        self.session_path = self.sessions_root / (utc_now().replace(':', '').replace('.', '') + '_' + session_id)
        self.session_info = dict(schema_version='1.0', session_id=session_id,
                                 agent='synthetic-demo' if demo else f'process-{pid}',
                                 mode='demo' if demo else 'attach', workspace=str(self.workspace),
                                 started_at=None, stopped_at=None, status='ready',
                                 platform=os.name, observer_pid=os.getpid(),
                                 machine={'os': platform.system(), 'release': platform.release(), 'architecture': platform.machine()},
                                 runtime={'python_version': platform.python_version()},
                                 limits={'file_content': 'not collected', 'file_reads': 'unavailable',
                                         'process_exit_codes': 'unavailable in attach mode',
                                         'workspace_actor': 'unverified', 'system_metrics': 'machine aggregate'})
        self.normalizer = Normalizer(session_id, self.session_info['agent'])
        self.engine = StateEngine()
        self.bus = EventBus()
        self.display = Queue(maxsize=2048)
        self.display_dropped_count = 0
        self._stop = threading.Event()
        self._thread = None
        self.status = 'ready'
        self.error = None

    @property
    def current_state(self):
        return self.engine.current

    @property
    def dropped_count(self):
        return self.bus.dropped_count + self.display_dropped_count

    def start(self):
        if self._thread is not None:
            raise RuntimeError('A controller runs only one session')
        self.status = 'starting'
        self._thread = threading.Thread(target=self._run, name='APM observation', daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self.status in ('starting', 'recording'):
            self.status = 'stopping'

    def wait(self, timeout=15):
        if self._thread:
            self._thread.join(timeout)
            return not self._thread.is_alive()
        return True

    def drain(self, limit=200):
        events = []
        for _ in range(limit):
            try:
                events.append(self.display.get_nowait())
            except Empty:
                break
        return events

    def _display_event(self, event):
        try:
            self.display.put_nowait(event)
        except Full:
            # Preserve newest visible evidence; recorder already received both.
            try:
                self.display.get_nowait()
            except Empty:
                pass
            self.display_dropped_count += 1
            self.display.put_nowait(event)

    def _emit(self, payload):
        from apm.interpreters.tests import interpret_test
        event = self.normalizer.normalize(payload)
        self.bus.publish(event)
        derived = interpret_test(event)
        if derived:
            self.bus.publish(self.normalizer.normalize(derived))

    def _run(self):
        recorder = None
        adapters = []
        try:
            self.session_info.update(started_at=utc_now(), status='recording')
            recorder = Recorder(self.session_path, self.session_info)
            self.bus.subscribe(recorder.record)
            def state_consumer(event):
                derived = self.engine.accept(event)
                if derived:
                    recorder.record_state(derived)
            self.bus.subscribe(state_consumer)
            self.bus.subscribe(self._display_event)
            self.status = 'recording'
            self._emit(dict(source='session-controller', category='session', action='START',
                            target='DEMO / SYNTHETIC' if self.demo else 'Observation active',
                            status='synthetic' if self.demo else 'observed',
                            interpretation_level='synthetic' if self.demo else 'observation',
                            metadata={'pid': self.pid, 'workspace': str(self.workspace), 'mode': self.session_info['mode']}))
            if not self.demo:
                from apm.observers.process import ProcessObserver
                from apm.observers.filesystem import FileSystemObserver
                from apm.observers.git import GitObserver
                from apm.observers.system import SystemObserver
                adapters = [(ProcessObserver(self.pid), 1.0),
                            (FileSystemObserver(self.workspace, excluded_roots=[self.sessions_root]), 2.0),
                            (GitObserver(self.workspace), 10.0), (SystemObserver(), 2.0)]
            due = [0.0] * len(adapters)
            demo = iter(demo_payloads())
            demo_due = 0.0
            checkpoint_due = 0.0
            while not self._stop.is_set():
                now = time.monotonic()
                if self.demo and now >= demo_due:
                    try:
                        self._emit(next(demo))
                        demo_due = now + .7
                    except StopIteration:
                        break
                for index, (adapter, interval) in enumerate(adapters):
                    if self._stop.is_set():
                        break
                    if now >= due[index]:
                        try:
                            for payload in adapter.poll():
                                self._emit(payload)
                        except Exception as exc:
                            self._emit(dict(source=adapter.name, category='error', action='UNKNOWN',
                                            status='unavailable', confidence=0.0,
                                            target='Adapter observation unavailable', metadata={'error': redact_text(str(exc))}))
                        due[index] = time.monotonic() + interval
                self.bus.dispatch()
                recorder.flush()
                if now >= checkpoint_due:
                    recorder.checkpoint(dict(heartbeat_at=utc_now(), dropped_events=self.bus.dropped_count,
                                             display_dropped_events=self.display_dropped_count,
                                             current_state=self.engine.current.to_dict()))
                    checkpoint_due = now + 5
                self._stop.wait(.1)
            self._emit(dict(source='session-controller', category='session', action='STOP',
                            target='Observation ended; no attached processes terminated',
                            status='synthetic' if self.demo else 'observed',
                            interpretation_level='synthetic' if self.demo else 'observation',
                            metadata={'dropped_events': self.bus.dropped_count, 'display_dropped_events': self.display_dropped_count}))
            while self.bus.dispatch():
                pass
            self.status = 'stopped'
        except Exception as exc:
            self.error = redact_text(f'{type(exc).__name__}: {exc}')
            self.status = 'error'
        finally:
            for adapter, _ in adapters:
                try:
                    adapter.close()
                except Exception:
                    pass
            self.session_info.update(status=self.status, stopped_at=utc_now(), error=self.error,
                                     dropped_events=self.bus.dropped_count,
                                     display_dropped_events=self.display_dropped_count,
                                     current_state=self.engine.current.to_dict())
            if recorder:
                try:
                    recorder.close(self.session_info)
                except OSError as exc:
                    self.error = redact_text(f'Recording failed: {exc}')
                    self.status = 'error'
