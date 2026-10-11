"""Append-only interpretations, separate from evidence. Unkeyed integrity, no authenticity."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

from apm.core.events import utc_now
from apm.evidence.capsule import identifier, timestamp
from apm.storage.memory import canonical
from .model import STATES, check, hypothesis, inventory, text
from apm.security.redaction import sanitize
from .challenge import challenge

APP_ID = 1095781704
MAX_ENTRIES = 2000
MAX_ENTRY = 65536
MAX_DB = 160 * 1024 * 1024
KINDS = ('CREATE', 'REVISE', 'REVIEW', 'CORRECT', 'CHALLENGE', 'VERIFICATION', 'PATTERN')
ZERO = '0' * 64


def chain(previous, body):
    return hashlib.sha256(b'APM-Holmes-journal-v1\0' + bytes.fromhex(previous) + body).hexdigest()


class Journal:
    def __init__(self, path):
        self.path = Path(path).resolve()
        check(self.path.is_file() and self.path.stat().st_size <= MAX_DB, 'journal_unavailable_or_large')
        self.db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=3)
        try:
            self.db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_ENTRY * 2)
            self.db.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
            self.db.execute('PRAGMA trusted_schema=OFF')
            check(self.db.execute('PRAGMA application_id').fetchone()[0] == APP_ID and
                  self.db.execute('PRAGMA user_version').fetchone()[0] == 1, 'journal_format')
            self.db.execute('PRAGMA synchronous=FULL')
            self.verify()
        except BaseException:
            self.db.close()
            raise

    @classmethod
    def create(cls, path):
        path = Path(path).resolve()
        check(path.suffix == '.sqlite3', 'journal_extension')
        with path.open('xb'):
            pass
        db = sqlite3.connect(path)
        try:
            db.executescript(f'''
                PRAGMA application_id={APP_ID}; PRAGMA user_version=1;
                PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
                CREATE TABLE entries(seq INTEGER PRIMARY KEY, request TEXT UNIQUE NOT NULL,
                    request_hash TEXT NOT NULL, entity TEXT NOT NULL, body BLOB NOT NULL,
                    previous TEXT NOT NULL, fingerprint TEXT NOT NULL);
                CREATE INDEX entity_history ON entries(entity,seq);
                CREATE TRIGGER no_update BEFORE UPDATE ON entries BEGIN SELECT RAISE(ABORT,'append_only'); END;
                CREATE TRIGGER no_delete BEFORE DELETE ON entries BEGIN SELECT RAISE(ABORT,'append_only'); END;
            ''')
        finally:
            db.close()
        return cls(path)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    @contextmanager
    def snapshot(self):
        check(not self.db.in_transaction, 'transaction_active')
        self.db.execute('BEGIN')
        self._reading_snapshot = True
        try:
            yield
        finally:
            self._reading_snapshot = False
            self.db.rollback()

    def verify(self, expected_tip=None):
        # One bounded read transaction; reject foreign/corrupt journals before appending.
        own_transaction = not self.db.in_transaction
        check(own_transaction or getattr(self, '_reading_snapshot', False), 'transaction_active')
        deadline = time.monotonic() + 10
        self.db.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
        if own_transaction: self.db.execute('BEGIN')
        try:
            check(self.db.execute('PRAGMA quick_check').fetchone()[0] == 'ok', 'sqlite_integrity')
            count, size = self.db.execute('SELECT count(*),coalesce(sum(length(body)),0) FROM entries').fetchone()
            check(count <= MAX_ENTRIES and size <= MAX_ENTRIES * MAX_ENTRY, 'journal_limit')
            previous, histories, seq = ZERO, {}, 0
            for seq, request, request_hash, entity, body, prior, tip in self.db.execute('SELECT * FROM entries ORDER BY seq'):
                check(time.monotonic() <= deadline, 'verification_timeout')
                check(isinstance(body, bytes) and len(body) <= MAX_ENTRY, 'entry_size')
                check(seq == sum(histories.values()) + 1 and prior == previous and chain(prior, body) == tip, 'journal_chain')
                value = json.loads(body)
                check(canonical(value) == body, 'noncanonical_entry')
                self._validate_entry(value)
                check(value['hypothesis_id'] == entity and value['request_id'] == request and
                      value['request_hash'] == request_hash, 'journal_index')
                check(value['revision'] == histories.get(entity, 0) + 1, 'revision_chain')
                check((entity not in histories) == (value['kind'] == 'CREATE'), 'creation_history')
                histories[entity] = value['revision']
                previous = tip
            check(expected_tip is None or previous == expected_tip, 'unexpected_tip')
            return dict(status='VERIFIED', check='SQLite quick_check and unkeyed journal chain/index/revision consistency',
                        entries=count, tip=previous, authenticity='UNVERIFIED')
        finally:
            if own_transaction: self.db.rollback()
            self.db.set_progress_handler(None, 0)

    @staticmethod
    def _validate_entry(value):
        check(set(value) == {'schema', 'case_id', 'title', 'purpose', 'hypothesis_id', 'revision', 'kind',
            'created_at', 'producer', 'producer_class', 'classification', 'state', 'hypothesis', 'detail', 'inventory',
            'request_id', 'request_hash', 'execution_authority'}, 'entry_fields')
        check(value['schema'] == 1 and value['kind'] in KINDS and value['state'] in STATES and
              value['execution_authority'] == 'NONE', 'entry_contract')
        for field in ('case_id', 'hypothesis_id', 'request_id'):
            identifier(value[field])
        timestamp(value['created_at'])
        check(type(value['revision']) is int and value['revision'] >= 1, 'revision')
        check(hypothesis(value['hypothesis']) == value['hypothesis'], 'unsanitized_hypothesis')
        for field in ('producer', 'title', 'purpose'):
            check(text(value[field]) == value[field], 'unsanitized_text')
        check(value['producer_class'] in ('HUMAN_RECORDED', 'AGENT_REPORTED', 'SYNTHETIC') and
              value['classification'] == ('INFERRED' if value['kind'] == 'CHALLENGE' else value['producer_class']), 'classification')
        if value['kind'] in ('REVIEW', 'CORRECT', 'PATTERN'):
            check(value['producer_class'] in ('HUMAN_RECORDED', 'SYNTHETIC'), 'human_review_required')
        # Recheck imported journal text before it can enter queues, displays or reports.
        check(sanitize(value) == value, 'unsafe_or_overdeep_entry')
        if value['kind'] == 'PATTERN':
            from .patterns import definition
            check(definition(value['detail']) == value['detail'], 'invalid_pattern_entry')
        elif value['kind'] == 'CREATE':
            check(value['detail'] == {} and value['state'] == 'PROPOSED', 'creation_contract')
        elif value['kind'] in ('REVIEW', 'CORRECT'):
            check(set(value['detail']) == {'state', 'reason'} and value['detail']['state'] == value['state'], 'assessment_contract')
            text(value['detail']['reason'])
        elif value['kind'] == 'REVISE':
            check(set(value['detail']) == {'hypothesis', 'reason'} and value['detail']['hypothesis'] == value['hypothesis'] and
                  value['state'] == 'PROPOSED', 'revision_contract')
            text(value['detail']['reason'])
        elif value['kind'] == 'VERIFICATION':
            detail = value['detail']
            check(set(detail) == {'procedure', 'outcome', 'limitations', 'references'} and
                  detail['outcome'] in ('REPORTED_PASS', 'REPORTED_FAIL', 'UNAVAILABLE'), 'verification_contract')
            text(detail['procedure']); text(detail['limitations'])
            from .model import refs
            refs(detail['references'])
        elif value['kind'] == 'CHALLENGE':
            check(value['detail'].get('algorithm') == 'apm-holmes-challenge-v1' and
                  value['detail'].get('execution_authority') == 'NONE' and value['detail'].get('status') == 'INFERRED', 'challenge_contract')

    def history(self, hypothesis_id=None, after=0, limit=100):
        check(type(after) is int and after >= 0 and type(limit) is int and 1 <= limit <= 100, 'page_bounds')
        if hypothesis_id is not None:
            identifier(hypothesis_id)
        sql = 'SELECT seq,body FROM entries WHERE seq>?'
        args = [after]
        if hypothesis_id:
            sql += ' AND entity=?'; args.append(hypothesis_id)
        sql += ' ORDER BY seq LIMIT ?'; args.append(limit)
        return [dict(sequence=seq, **json.loads(body)) for seq, body in self.db.execute(sql, args)]

    def all_entries(self):
        if not self.db.in_transaction:
            with self.snapshot():
                return self.all_entries()
        after, result = 0, []
        while page := self.history(after=after):
            result.extend(page); after = page[-1]['sequence']
        return result

    def latest(self, hypothesis_id):
        identifier(hypothesis_id)
        row = self.db.execute('SELECT body FROM entries WHERE entity=? ORDER BY seq DESC LIMIT 1', (hypothesis_id,)).fetchone()
        check(row is not None, 'hypothesis_unknown')
        return json.loads(row[0])

    def _append(self, request_id, request, build):
        identifier(request_id)
        request_hash = hashlib.sha256(canonical(request)).hexdigest()
        with self.transaction():
            old = self.db.execute('SELECT request_hash,body FROM entries WHERE request=?', (request_id,)).fetchone()
            if old:
                check(old[0] == request_hash, 'request_conflict')
                return json.loads(old[1])
            check(self.db.execute('SELECT count(*) FROM entries').fetchone()[0] < MAX_ENTRIES, 'journal_full')
            value = build()
            value.update(schema=1, request_id=request_id, request_hash=request_hash,
                         created_at=utc_now(), execution_authority='NONE')
            self._validate_entry(value)
            body = canonical(value)
            check(len(body) <= MAX_ENTRY, 'entry_too_large')
            row = self.db.execute('SELECT seq,fingerprint FROM entries ORDER BY seq DESC LIMIT 1').fetchone()
            seq, previous = (row[0]+1, row[1]) if row else (1, ZERO)
            self.db.execute('INSERT INTO entries VALUES(?,?,?,?,?,?,?)',
                (seq, request_id, request_hash, value['hypothesis_id'], body, previous, chain(previous, body)))
            return value

    def propose(self, case_id, title, purpose, producer, value, catalog, *, request_id, producer_class='HUMAN_RECORDED'):
        identifier(case_id)
        value = hypothesis(value, catalog)
        title, purpose, producer = text(title), text(purpose), text(producer, 200)
        request = dict(operation='CREATE', case_id=case_id, title=title, purpose=purpose, producer=producer,
                       producer_class=producer_class, hypothesis=value)
        def build():
            return dict(case_id=case_id, title=title, purpose=purpose, producer=producer, hypothesis=value,
                hypothesis_id=str(uuid4()), revision=1, kind='CREATE', classification=producer_class, producer_class=producer_class,
                state='PROPOSED', detail={}, inventory=inventory(catalog, value))
        return self._append(request_id, request, build)

    def revise(self, hypothesis_id, expected_revision, producer, kind, detail, catalog, *, request_id, producer_class='HUMAN_RECORDED'):
        identifier(hypothesis_id)
        check(kind in KINDS and kind != 'CREATE', 'operation_not_allowed')
        check(type(expected_revision) is int and expected_revision >= 1, 'revision')
        producer = text(producer, 200)
        check(isinstance(detail, dict), 'detail')
        if kind in ('REVIEW', 'CORRECT'):
            check(set(detail) == {'state', 'reason'} and detail['state'] in STATES, 'review_fields')
            detail = dict(state=detail['state'], reason=text(detail['reason']))
        elif kind == 'REVISE':
            check(set(detail) == {'hypothesis', 'reason'}, 'revision_fields')
            detail = dict(hypothesis=hypothesis(detail.get('hypothesis'), catalog), reason=text(detail.get('reason')))
        elif kind == 'CHALLENGE':
            check(not detail, 'challenge_fields')
        elif kind == 'VERIFICATION':
            check(set(detail) == {'procedure', 'outcome', 'limitations', 'references'} and
                  detail['outcome'] in ('REPORTED_PASS', 'REPORTED_FAIL', 'UNAVAILABLE'), 'verification_fields')
            from .model import refs
            detail = dict(procedure=text(detail['procedure']), outcome=detail['outcome'],
                          limitations=text(detail['limitations']), references=refs(detail['references']))
            for ref in detail['references']:
                catalog.resolve(ref)
        elif kind == 'PATTERN':
            from .patterns import definition
            detail = definition(detail)
        request = dict(operation=kind, hypothesis_id=hypothesis_id, expected_revision=expected_revision,
                       producer=producer, producer_class=producer_class, detail=detail)
        def build():
            previous = self.latest(hypothesis_id)
            check(previous['revision'] == expected_revision, 'stale_revision')
            current = dict(previous)
            current.update(revision=expected_revision+1, kind=kind, producer=producer,
                           producer_class=producer_class, classification='INFERRED' if kind == 'CHALLENGE' else producer_class)
            if kind == 'PATTERN':
                entries = self.all_entries()
                reviews = [e for e in entries if e['hypothesis_id'] == hypothesis_id and e['revision'] == detail['source_review_revision']]
                check(len(reviews) == 1 and reviews[0]['kind'] in ('REVIEW', 'CORRECT') and
                      reviews[0]['state'] == 'SUPPORTED_WITH_LIMITATIONS', 'pattern_requires_supported_human_review')
                # Promotion requires evidence, all still accessible. Human assent alone is insufficient.
                reviewed = reviews[0]['hypothesis']
                check(bool(reviewed['support']), 'pattern_requires_evidence')
                if reviews[0]['producer_class'] == 'SYNTHETIC' or producer_class == 'SYNTHETIC':
                    check(detail['required'].get('evidence_class') == 'SYNTHETIC', 'synthetic_review_only_matches_synthetic')
                if detail['disposition'] == 'ACTIVE':
                    from .patterns import matches, needs_reassessment
                    check(not needs_reassessment(entries, hypothesis_id, detail['source_review_revision']), 'pattern_review_stale')
                    for ref in reviewed['support'] + reviewed['contradict']:
                        catalog.resolve(ref)
                    check(any(matches(detail['required'], catalog.resolve(ref)) for ref in reviewed['support']), 'pattern_no_supporting_example')
                patterns = [e for e in entries if e['kind'] == 'PATTERN']
                ids = {e['detail']['pattern_id'] for e in patterns}
                check(detail['pattern_id'] in ids or len(ids) < 100, 'pattern_limit')
                prior = [e for e in patterns if e['detail']['pattern_id'] == detail['pattern_id']]
                check(detail['version'] == (prior[-1]['detail']['version'] + 1 if prior else 1), 'pattern_version')
                if prior:
                    check(prior[-1]['hypothesis_id'] == hypothesis_id, 'pattern_source_mismatch')
                else:
                    check(detail['disposition'] == 'ACTIVE', 'pattern_must_start_active')
            if kind == 'CORRECT':
                check(any(e['kind'] in ('REVIEW', 'CORRECT') for e in self.all_entries()
                          if e['hypothesis_id'] == hypothesis_id), 'no_assessment_to_correct')
            if kind == 'REVISE':
                current['hypothesis'] = detail['hypothesis']
                current['state'] = 'PROPOSED'
                current['inventory'] = inventory(catalog, current['hypothesis'])
            elif kind in ('REVIEW', 'CORRECT'):
                current['state'] = detail['state']
            current['detail'] = challenge(current['hypothesis'], catalog) if kind == 'CHALLENGE' else detail
            # Old metadata is assigned anew by _append; keep no incidental sequence field.
            return current
        return self._append(request_id, request, build)

    def backup(self, destination):
        self.verify()
        destination = Path(destination)
        with destination.open('xb'):
            pass
        target = sqlite3.connect(destination)
        try:
            self.db.backup(target)
        finally:
            target.close()
        with Journal(destination) as copied:
            return copied.verify()
