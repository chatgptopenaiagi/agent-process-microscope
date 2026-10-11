"""Read-only, full-session review of a bounded consistent SQLite snapshot."""
from collections import Counter
import json
import time
from uuid import UUID

from apm.security.redaction import sanitize
from apm.storage.memory import Memory, GENESIS, clean_event, classification


class QualificationReview:
    def __init__(self, path, *, expected_tip=None, cancelled=lambda: False):
        self.memory = Memory.read_snapshot(path, cancelled=cancelled)
        self.db = self.memory.db
        self.cancelled = cancelled
        deadline = time.monotonic() + 60
        self.db.set_progress_handler(lambda: int(cancelled() or time.monotonic() > deadline), 1000)
        try:
            self.integrity = self.memory.verify(expected_tip)
            self.available = self.integrity['ok']
        except Exception:
            self.memory.close()
            raise
        finally:
            if hasattr(self, 'integrity'):
                self.db.set_progress_handler(lambda: int(cancelled()), 1000)

    def close(self):
        self.memory.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _require(self):
        if not self.available:
            raise ValueError('integrity_failed_evidence_display_disabled')
        if self.cancelled():
            raise ValueError('review_cancelled')

    def sessions(self):
        self._require()
        return self.memory.sessions()

    def _record(self, row):
        body = json.loads(row['body'])
        event = clean_event(body['event'])
        # Reclassify from the recorded origin/status, never trust a display label.
        if body['evidence_class'] != classification(event, body['origin']):
            raise ValueError('inconsistent_evidence_class')
        body = sanitize(body)
        body['event'] = event
        return dict(arrival=row['arrival'], fingerprint=row['fingerprint'], **body)

    def page(self, session, *, after=0, limit=100):
        self._require()
        return self._page(str(UUID(session)), after, limit)

    def _page(self, session, after, limit):
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('review_page_bounds')
        rows = self.db.execute('SELECT * FROM records WHERE session_id=? AND arrival>? ORDER BY arrival LIMIT ?',
                               (session, after, limit)).fetchall()
        return [self._record(row) for row in rows]

    def resolve(self, session, evidence_id):
        self._require()
        row = self.db.execute('SELECT * FROM records WHERE session_id=? AND event_id=?',
                              (str(UUID(session)), str(UUID(evidence_id)))).fetchone()
        return self._record(row) if row else None

    def citations(self, session, evidence_id):
        record = self.resolve(session, evidence_id)
        if record is None:
            return dict(checkpoint='UNKNOWN: selected record unavailable', references=[])
        meta = record['event']['metadata']
        refs = meta.get('evidence_ids', [])
        if not isinstance(refs, list) or len(refs) > 100:
            raise ValueError('citation_bounds')
        references = []
        for ref in refs:
            try:
                target = self.resolve(session, ref)
            except (ValueError, TypeError, AttributeError):
                target = None
            references.append(dict(evidence_id=sanitize(str(ref)), record=target,
                                   status='resolved' if target else 'UNKNOWN: missing or outside selected session'))
        through, tip = meta.get('through_arrival'), meta.get('checkpoint')
        checkpoint = 'UNKNOWN: no saved investigation checkpoint'
        if type(through) is int and isinstance(tip, str):
            row = self.db.execute('SELECT fingerprint FROM records WHERE session_id=? AND arrival=?',
                                   (str(UUID(session)), through)).fetchone()
            matches = through < record['arrival'] and ((row and row[0] == tip) or (through == 0 and tip == GENESIS))
            checkpoint = ('MATCHES' if matches else 'MISMATCH') + f': saved receipt {through}, chain tip {sanitize(tip)}'
        return dict(checkpoint=checkpoint, references=references)

    def summary(self, session):
        self._require()
        session = str(UUID(session))
        counts = Counter()
        classes = Counter()
        cursor, tip = 0, GENESIS
        # Track only outcomes for the same producer stream and public item ID.
        outcomes = {}
        turns = Counter()
        while True:
            self._require()
            rows = self._page(session, cursor, 100)
            if not rows:
                break
            for r in rows:
                e = r['event']; meta = e['metadata']; kind = r['evidence_class']
                counts['records'] += 1; classes[kind] += 1
                counts['sequence_gaps'] += r['missing_before']
                if r['origin'] == 'host' and kind == 'OBSERVED' and e['category'] == 'process' and meta.get('create_time') is not None:
                    counts['host_process_records'] += 1
                    if meta.get('pid') is not None and meta.get('root_pid') is not None and meta['pid'] != meta['root_pid']:
                        counts['child_process_records'] += 1
                if r['origin'] == 'local-investigator':
                    counts['saved_investigations'] += 1
                    citations = self.citations(session, e['event_id'])
                    counts['missing_citations'] += sum(x['record'] is None for x in citations['references'])
                    counts['checkpoint_mismatches'] += citations['checkpoint'].startswith('MISMATCH')
                if kind == 'AGENT_REPORTED' and e['source'] == 'codex':
                    counts['codex_reports'] += 1
                    if meta.get('codex_event') == 'turn.started':
                        turns[r['stream']] += 1
                    if meta.get('codex_event') == 'turn.completed':
                        counts['completed_turn_reports'] += 1
                    if (e['category'] == 'command' and meta.get('codex_event') == 'item.completed'
                            and type(meta.get('exit_code')) is int):
                        counts['failed_command_reports'] += meta['exit_code'] != 0
                        item = meta.get('item_id')
                        if isinstance(item, str):
                            key = (r['stream'], turns[r['stream']], item)
                            old = outcomes.setdefault(key, meta['exit_code'])
                            if old != meta['exit_code']:
                                counts['contradictory_outcome_reports'] += 1
                cursor, tip = r['arrival'], r['fingerprint']
        return dict(session=session, counts=dict(counts), classes=dict(classes),
                    through_arrival=cursor, session_tip=tip, integrity=self.integrity)


def summary_text(summary):
    c = Counter(summary['counts'])
    return '\n'.join([
        f"Full selected session: {c['records']} retained records; all pages included in this summary.",
        f"Codex reports: {c['codex_reports']}; reported command failures: {c['failed_command_reports']}; completed turn reports: {c['completed_turn_reports']}.",
        f"Independent host process-generation observations: {c['host_process_records']} records, including {c['child_process_records']} child records (not unique-process counts).",
        f"Saved investigations: {c['saved_investigations']}; missing citations: {c['missing_citations']}; checkpoint mismatches: {c['checkpoint_mismatches']}.",
        f"Missing sequence records: {c['sequence_gaps']}; contradictory same-item outcome reports: {c['contradictory_outcome_reports']}.",
        'Evidence classes: ' + ', '.join(f'{k}={v}' for k, v in sorted(summary['classes'].items())),
        f"Session last receipt: {summary['through_arrival']}; recorded chain tip: {summary['session_tip']}",
        f"Verified database snapshot: {summary['integrity']['records']} records; tip: {summary['integrity']['tip']}",
        'This summary is a local inference about retained evidence. A reported failure does not establish its cause. Absence of reports does not prove success.',
        'OBSERVED = host observation; AGENT_REPORTED = producer claim; INFERRED = interpretation; SYNTHETIC = fixture; UNKNOWN/UNAVAILABLE = missing knowledge; HUMAN_RECORDED = unverified opinion.',
        'UNKNOWN: account identity, source authenticity, command-to-process causation and completeness. Time proximity and process ancestry do not prove causation. No bidirectional cooperation is claimed.',
    ])
