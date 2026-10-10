"""Durable sanitized outbox; stop at capacity, retry stable IDs after outage."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from apm.core.events import Normalizer

from apm.storage.memory import canonical, clean_event
from .transport import request


class Outbox:
    def __init__(self, path, *, capacity=1000):
        if type(capacity) is not int or not 1 <= capacity <= 10000:
            raise ValueError('outbox_capacity')
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.capacity = capacity
        try:
            app = self.db.execute('PRAGMA application_id').fetchone()[0]
            version = self.db.execute('PRAGMA user_version').fetchone()[0]
            if app == 0 and version == 0:
                if self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
                    raise ValueError('not_an_apm_outbox')
                self.db.executescript('''BEGIN IMMEDIATE;
                    CREATE TABLE identity(stream TEXT, next_seq INTEGER, session_id TEXT, lost INTEGER);
                    CREATE TABLE pending(seq INTEGER PRIMARY KEY, event TEXT NOT NULL);
                    PRAGMA application_id=1095781682;
                    PRAGMA user_version=1;
                    COMMIT;''')
                with self.db:
                    self.db.execute('INSERT INTO identity VALUES(?,1,NULL,0)', (str(uuid4()),))
            elif app != 1095781682 or version != 1:
                raise ValueError('unsupported_outbox_schema')
            self.db.execute('PRAGMA synchronous=FULL')
        except Exception:
            self.db.close()
            raise
        self.stream = self.db.execute('SELECT stream FROM identity').fetchone()[0]

    def close(self):
        self.db.close()

    def enqueue(self, event):
        event = clean_event(event)
        encoded = canonical(event).decode('ascii')
        full = False
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            session = self.db.execute('SELECT session_id FROM identity').fetchone()[0]
            if session is not None and session != event['session_id']:
                raise ValueError('outbox_session_conflict')
            self.db.execute('UPDATE identity SET session_id=?', (event['session_id'],))
            if self.db.execute('SELECT count(*) FROM pending').fetchone()[0] >= self.capacity:
                self.db.execute('UPDATE identity SET lost=lost+1')
                full = True
            else:
                seq = self.db.execute('SELECT next_seq FROM identity').fetchone()[0]
                self.db.execute('INSERT INTO pending VALUES(?,?)', (seq, encoded))
                self.db.execute('UPDATE identity SET next_seq=next_seq+1')
        if full:
            raise ValueError('outbox_full_source_stopped_loss_count_retained')
        return seq

    @property
    def pending(self):
        return (self.db.execute('SELECT count(*) FROM pending').fetchone()[0]
                + bool(self.db.execute('SELECT lost FROM identity').fetchone()[0]))

    def _materialize_loss(self):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            stream, seq, session, lost = self.db.execute('SELECT * FROM identity').fetchone()
            if not lost or self.db.execute('SELECT count(*) FROM pending').fetchone()[0] >= self.capacity:
                return
            event = Normalizer(session, 'companion').normalize(dict(source='companion-health',
                category='session', action='UNKNOWN', status='unavailable', confidence=0.0,
                target='Outbox overflow stopped source collection; later source activity is unavailable.',
                metadata={'dropped_events':lost, 'coverage':'At least these consumed records were not retained.'}))
            self.db.execute('INSERT INTO pending VALUES(?,?)', (seq, canonical(event.to_dict()).decode('ascii')))
            self.db.execute('UPDATE identity SET next_seq=next_seq+1,lost=0')

    def flush(self, port, credential, *, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError('flush_limit')
        self._materialize_loss()
        sent = 0
        rows = self.db.execute('SELECT seq,event FROM pending ORDER BY seq LIMIT ?', (limit,)).fetchall()
        while rows:
            batch, size = [], 0
            for seq, event in rows[:32]:
                entry = dict(event=json.loads(event), stream=self.stream, sequence=seq)
                cost = len(canonical(entry)) + 1
                if batch and size + cost > 60000:
                    break
                batch.append(entry); size += cost
            request(port, credential, 'append_batch', entries=batch)
            with self.db:
                self.db.executemany('DELETE FROM pending WHERE seq=?', [(entry['sequence'],) for entry in batch])
            sent += len(batch)
            rows = rows[len(batch):]
        self._materialize_loss()
        return sent
