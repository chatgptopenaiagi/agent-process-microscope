"""Local operational memory. Receipt order is not execution order or causality."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from contextlib import closing, contextmanager
from uuid import UUID, uuid4

from apm.core.events import Event, Normalizer, utc_now

DOMAIN = b'APM-memory-v1\x00'
GENESIS = '0' * 64
MAX_EVENT_BYTES = 32768


def canonical(value):
    """APM Python JSON profile, deliberately not a claim of RFC 8785 compliance."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def clean_event(value):
    if not isinstance(value, dict) or len(canonical(value)) > MAX_EVENT_BYTES:
        raise ValueError('event_size_or_type')
    if set(value) != set(Event.__dataclass_fields__):
        raise ValueError('event_fields')
    event = Event.from_dict(value).to_dict()
    event['event_id'] = str(UUID(event['event_id']))
    event['session_id'] = str(UUID(event['session_id']))
    return event


def classification(event, origin):
    if event['status'] in ('synthetic', 'inferred', 'unknown', 'unavailable'):
        return event['status'].upper()
    if origin == 'local-human':
        return 'HUMAN_RECORDED'
    return 'OBSERVED' if origin == 'host' else 'AGENT_REPORTED'


class Memory:
    """Serialized short transactions; WAL readers use their own connections.

    No pruning: fail explicitly at the configured logical cap. Owner can back up
    and select a fresh database. Existing JSONL recordings are never modified.
    """
    def __init__(self, path, *, readonly=False, max_records=100000, max_bytes=128*1024*1024):
        if not 1 <= max_records <= 1000000 or not 1024 <= max_bytes <= 1024**3:
            raise ValueError('memory_limits')
        self.path = Path(path).resolve()
        self.lock = threading.RLock()
        self.max_records, self.max_bytes = max_records, max_bytes
        if readonly:
            self.db = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True,
                                      timeout=3, check_same_thread=False)
            self.db.execute('PRAGMA query_only=ON')
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(self.path, timeout=3, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        try:
            version = self.db.execute('PRAGMA user_version').fetchone()[0]
            app = self.db.execute('PRAGMA application_id').fetchone()[0]
            if version == 0 and not readonly:
                if self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
                    raise ValueError('not_an_apm_database')
                self.db.executescript('''BEGIN IMMEDIATE;
                    CREATE TABLE records (
                        arrival INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL,
                        session_id TEXT NOT NULL, stream TEXT NOT NULL, seq INTEGER NOT NULL,
                        body TEXT NOT NULL, previous TEXT NOT NULL, fingerprint TEXT NOT NULL,
                        UNIQUE(stream, seq));
                    CREATE INDEX session_arrival ON records(session_id, arrival);
                    CREATE TABLE counters (id INTEGER PRIMARY KEY CHECK(id=1), n INTEGER, bytes INTEGER);
                    INSERT INTO counters VALUES(1, 0, 0);
                    PRAGMA application_id=1095781681;
                    PRAGMA user_version=1;
                    COMMIT;''')
            elif version != 1 or app != 1095781681:
                raise ValueError('unsupported_memory_schema')
            if not readonly:
                self.db.execute('PRAGMA journal_mode=WAL')
                self.db.execute('PRAGMA synchronous=FULL')
                self.db.execute('PRAGMA wal_autocheckpoint=256')
                self.db.execute('PRAGMA journal_size_limit=4194304')
                self.db.execute('PRAGMA max_page_count=262144')
        except Exception:
            self.db.close()
            raise

    def close(self):
        with self.lock:
            self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @contextmanager
    def transaction(self):
        with self.lock:
            if self.db.in_transaction:
                yield
            else:
                with self.db:
                    self.db.execute('BEGIN IMMEDIATE')
                    yield

    def append_batch(self, entries, *, origin='reporter', principal='local'):
        if not isinstance(entries, list) or not 1 <= len(entries) <= 32:
            raise ValueError('batch_bounds')
        with self.transaction():
            return [self.append(entry['event'], entry['stream'], entry['sequence'],
                                origin=origin, principal=principal) for entry in entries]

    def append(self, value, stream, seq, *, origin='reporter', principal='local'):
        event = clean_event(value)
        stream = str(UUID(stream))
        if type(seq) is not int or not 1 <= seq <= 2**53-1:
            raise ValueError('sequence_range')
        if origin not in ('host', 'reporter', 'local-investigator', 'local-human'):
            raise ValueError('origin')
        if not isinstance(principal, str) or not 1 <= len(principal) <= 80:
            raise ValueError('principal')
        with self.transaction():
            prior = self.db.execute('SELECT * FROM records WHERE event_id=? OR (stream=? AND seq=?)',
                                    (event['event_id'], stream, seq)).fetchone()
            if prior:
                old = json.loads(prior['body'])
                if (old['event'] != event or old['stream'] != stream or old['sequence'] != seq
                        or old['origin'] != origin or old['principal'] != principal):
                    raise ValueError('duplicate_conflict')
                return {'arrival': prior['arrival'], 'duplicate': True, 'fingerprint': prior['fingerprint']}
            last = self.db.execute('SELECT body, seq FROM records WHERE stream=? ORDER BY seq DESC LIMIT 1',
                                   (stream,)).fetchone()
            last_seq = last['seq'] if last else 0
            if last:
                old = json.loads(last['body'])
                if (old['event']['session_id'] != event['session_id'] or old['origin'] != origin
                        or old['principal'] != principal):
                    raise ValueError('stream_owner_conflict')
            if seq <= last_seq:
                raise ValueError('sequence_regression')
            body = dict(version=1, event=event, stream=stream, sequence=seq,
                        received_at=utc_now(), origin=origin, principal=principal,
                        evidence_class=classification(event, origin), missing_before=seq-last_seq-1)
            encoded = canonical(body)
            count = self.db.execute('SELECT n, bytes FROM counters WHERE id=1').fetchone()
            if count['n'] >= self.max_records or count['bytes'] + len(encoded) > self.max_bytes:
                raise ValueError('memory_full_archive_and_select_new_database')
            tip = self.db.execute('SELECT fingerprint FROM records ORDER BY arrival DESC LIMIT 1').fetchone()
            previous = tip[0] if tip else GENESIS
            fingerprint = hashlib.sha256(DOMAIN + bytes.fromhex(previous) + encoded).hexdigest()
            cursor = self.db.execute('INSERT INTO records(event_id,session_id,stream,seq,body,previous,fingerprint) VALUES(?,?,?,?,?,?,?)',
                                    (event['event_id'], event['session_id'], stream, seq,
                                     encoded.decode('ascii'), previous, fingerprint))
            self.db.execute('UPDATE counters SET n=n+1, bytes=bytes+? WHERE id=1', (len(encoded),))
            return {'arrival': cursor.lastrowid, 'duplicate': False, 'fingerprint': fingerprint}

    def events(self, session_id, *, after=0, limit=100, search=''):
        session_id = str(UUID(session_id))
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('query_bounds')
        if not isinstance(search, str) or len(search) > 120:
            raise ValueError('search_bounds')
        # Parameterized literal substring, no arbitrary SQL or LIKE wildcards.
        with self.lock:
            rows = self.db.execute('SELECT * FROM records WHERE session_id=? AND arrival>? AND instr(lower(body),lower(?))>0 ORDER BY arrival LIMIT ?',
                                   (session_id, after, search, limit)).fetchall()
        return [dict(arrival=r['arrival'], fingerprint=r['fingerprint'], **json.loads(r['body'])) for r in rows]

    def sessions(self):
        with self.lock:
            return [dict(r) for r in self.db.execute('SELECT session_id, count(*) AS events, max(arrival) AS latest FROM records GROUP BY session_id ORDER BY latest DESC LIMIT 100')]

    def investigate(self, session_id):
        """Bounded deterministic explanation of the last 100 receipt-ordered events."""
        session_id = str(UUID(session_id))
        with self.lock, self.db:
            self.db.execute('BEGIN')
            rows = self.db.execute('SELECT arrival, body, fingerprint FROM records WHERE session_id=? ORDER BY arrival DESC LIMIT 100', (session_id,)).fetchall()
            total = self.db.execute('SELECT count(*) FROM records WHERE session_id=?', (session_id,)).fetchone()[0]
        findings = []
        for row in reversed(rows):
            record = json.loads(row['body']); event = record['event']
            if record['origin'] in ('local-investigator', 'local-human'):
                continue
            meta = event['metadata']
            failed = event['action'] == 'FAIL' or (event['category'] == 'command' and
                         type(meta.get('exit_code')) is int and meta['exit_code'] != 0)
            unavailable = event['status'] in ('unknown', 'unavailable')
            if failed or unavailable or record['missing_before']:
                findings.append(dict(evidence_id=event['event_id'], evidence_class=record['evidence_class'],
                    text=('Failure reported' if failed else 'Observation gap or unavailable fact') + ': ' + event['target'],
                    missing_before=record['missing_before']))
        latest = next((json.loads(r['body']) for r in rows if json.loads(r['body'])['origin'] not in
                       ('local-investigator', 'local-human')), None)
        return dict(algorithm='local-rules-v1', session_id=session_id, inspected=len(rows), total=total,
                    truncated=total > len(rows), through_arrival=rows[0]['arrival'] if rows else 0,
                    checkpoint=rows[0]['fingerprint'] if rows else GENESIS, latest=latest,
                    findings=findings,
                    unknowns=['Current execution beyond the latest receipt is unknown.',
                              'Reported exit codes are not independent OS verification.',
                              'File changes and temporal proximity do not prove authorship or causation.',
                              'Failure output and private reasoning are not collected; root cause may be unavailable.'])

    def save_investigation(self, result):
        event = Normalizer(result['session_id'], 'local-rules').normalize(dict(
            source='local-investigator', category='verification', action='VERIFY',
            target=explanation(result), status='inferred', interpretation_level='inference',
            metadata={'algorithm': result['algorithm'], 'through_arrival': result['through_arrival'],
                      'checkpoint': result['checkpoint'], 'inspected': result['inspected'],
                      'total': result['total'], 'truncated': result['truncated'],
                      'evidence_ids': [f['evidence_id'] for f in result['findings']]}))
        return self.append(event.to_dict(), str(uuid4()), 1, origin='local-investigator')

    def note(self, session_id, text, *, decision='annotate', references=()):
        session_id = str(UUID(session_id))
        if decision not in ('annotate', 'approve', 'reject', 'investigate', 'correct'):
            raise ValueError('decision_kind')
        if not isinstance(text, str) or not 1 <= len(text) <= 2000 or len(references) > 20:
            raise ValueError('note_bounds')
        with self.lock:
            for ref in references:
                if not self.db.execute('SELECT 1 FROM records WHERE event_id=? AND session_id=?',
                                       (str(UUID(ref)), session_id)).fetchone():
                    raise ValueError('missing_evidence_reference')
        event = Normalizer(session_id, 'human-local').normalize(dict(source='human-decision', category='verification',
            action='UPDATE', target=text, metadata={'decision': decision, 'evidence_ids': list(references),
                'authority': 'Recorded opinion only; never execution permission. Human identity is not verified.'}))
        return self.append(event.to_dict(), str(uuid4()), 1, origin='local-human')

    def verify(self, expected_tip=None):
        with self.lock, self.db:
            self.db.execute('BEGIN')
            if self.db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                return {'ok': False, 'reason': 'sqlite_integrity'}
            previous, count, size = GENESIS, 0, 0
            streams = {}
            for row in self.db.execute('SELECT * FROM records ORDER BY arrival'):
                try:
                    body = json.loads(row['body']); encoded = canonical(body)
                    event = body['event']
                    expected = hashlib.sha256(DOMAIN + bytes.fromhex(previous) + encoded).hexdigest()
                    last = streams.get(row['stream'], 0)
                    valid = (row['previous'] == previous and row['fingerprint'] == expected
                             and row['event_id'] == event['event_id'] and row['session_id'] == event['session_id']
                             and row['stream'] == body['stream'] and row['seq'] == body['sequence']
                             and row['seq'] > last and body['missing_before'] == row['seq']-last-1)
                    if not valid:
                        return {'ok': False, 'reason': 'chain_or_index', 'arrival': row['arrival']}
                    streams[row['stream']] = row['seq']
                    previous = expected; count += 1; size += len(encoded)
                except (ValueError, KeyError, TypeError):
                    return {'ok': False, 'reason': 'malformed_record', 'arrival': row['arrival']}
            counters = self.db.execute('SELECT n, bytes FROM counters WHERE id=1').fetchone()
            return {'ok': (count, size) == tuple(counters) and (expected_tip is None or expected_tip == previous),
                    'records': count, 'tip': previous,
                    'limits': 'Unkeyed chain; no source authenticity or completeness proof. Keep an external tip to detect tail removal.'}

    def backup(self, destination):
        path = Path(destination).resolve()
        # Exclusive reservation prevents accidental overwrite of owner data.
        with path.open('xb'):
            pass
        with self.lock, closing(sqlite3.connect(path)) as target:
            self.db.backup(target)


def explanation(result):
    lines = [f"Local evidence review: {result['inspected']} of {result['total']} records (last 100 maximum)."]
    if result['latest']:
        r = result['latest']; e = r['event']
        lines.append(f"Latest receipt [{r['evidence_class']}]: {e['action']} {e['target']} [{e['event_id']}]")
    else:
        lines.append('UNKNOWN: No evidence retained for this session.')
    for finding in result['findings']:
        lines.append(f"[{finding['evidence_class']}] {finding['text']} [{finding['evidence_id']}]; missing sequence records: {finding['missing_before']}")
    if not result['findings']:
        lines.append('No failure or gap found in this bounded window; this is not proof of success or complete coverage.')
    lines.extend('UNKNOWN: ' + item for item in result['unknowns'])
    return '\n'.join(lines)
