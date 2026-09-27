"""Append-only JSONL plus atomically replaced metadata. No raw content store."""
from __future__ import annotations

import json
import os
from pathlib import Path
import time

from apm.security.redaction import sanitize


def atomic_json(path: Path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(sanitize(value), stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


class Recorder:
    def __init__(self, path: Path, info: dict):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=False)
        self.info = sanitize(info)
        atomic_json(self.path / 'session.json', self.info)
        self.events = (self.path / 'events.jsonl').open('x', encoding='utf-8', newline='\n')
        self.states = (self.path / 'derived_states.jsonl').open('x', encoding='utf-8', newline='\n')
        self.last_flush = time.monotonic()
        self.count = 0
        self.bytes_written = 0
        self.closed = False

    def record(self, event):
        encoded = json.dumps(sanitize(event.to_dict()), ensure_ascii=False, allow_nan=False) + '\n'
        if self.count >= 100_000 or self.bytes_written + len(encoded.encode('utf-8')) > 64 * 1024 * 1024:
            raise RuntimeError('Recording limit reached (100,000 events / 64 MiB); start a new session')
        self.events.write(encoded)
        self.bytes_written += len(encoded.encode('utf-8'))
        self.count += 1
        self.flush()

    def record_state(self, state):
        self.states.write(json.dumps(sanitize(state.to_dict()), ensure_ascii=False, allow_nan=False) + '\n')

    def flush(self, force=False):
        if force or time.monotonic() - self.last_flush >= 1:
            for stream in (self.events, self.states):
                stream.flush()
                os.fsync(stream.fileno())
            self.last_flush = time.monotonic()

    def checkpoint(self, updates):
        self.info.update(sanitize(updates))
        self.info['event_count'] = self.count
        atomic_json(self.path / 'session.json', self.info)

    def close(self, updates):
        if not self.closed:
            try:
                self.flush(force=True)
                self.checkpoint(updates)
            finally:
                try:
                    self.events.close()
                finally:
                    try:
                        self.states.close()
                    finally:
                        self.closed = True
