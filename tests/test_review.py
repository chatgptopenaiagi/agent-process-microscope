"""Sanitized fixtures only. Retained owner evidence is an explicit acceptance check."""
import hashlib
from pathlib import Path
import shutil
import sqlite3
import time
import tkinter as tk
import unittest
from contextlib import closing
from uuid import uuid4

from apm.core.events import Normalizer
from apm.storage.memory import Memory
from apm.storage.review import QualificationReview, summary_text
from apm.ui.qualification_window import QualificationWindow


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1] / 'cache' / ('review-tests-' + str(uuid4()))
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root)
        self.path = self.root / 'memory.sqlite3'
        self.session, self.stream = str(uuid4()), str(uuid4())
        self.normalizer = Normalizer(self.session, 'fixture')

    def event(self, **overrides):
        return self.normalizer.normalize(dict(source='fixture', category='test', action='PASS',
            status='synthetic', interpretation_level='synthetic', target='Sanitized fixture') | overrides).to_dict()

    def fill(self, count=205):
        with Memory(self.path) as m:
            for seq in range(1, count+1):
                m.append(self.event(), self.stream, seq)

    def test_complete_pagination_counts_and_readonly_snapshot(self):
        self.fill()
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with QualificationReview(self.path) as r:
            pages = [r.page(self.session, after=n) for n in (0, 100, 200, 205)]
            self.assertEqual([len(p) for p in pages], [100, 100, 5, 0])
            self.assertEqual(len({x['event']['event_id'] for p in pages for x in p}), 205)
            self.assertEqual(r.summary(self.session)['classes'], {'SYNTHETIC': 205})
            with self.assertRaises(sqlite3.OperationalError):
                r.db.execute('DELETE FROM records')
            with Memory(self.path) as writer:
                writer.append(self.event(), self.stream, 206)
            self.assertEqual(r.summary(self.session)['counts']['records'], 205)
        # The separately authorized fixture writer appended; a fresh review sees it.
        after_writer = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.assertNotEqual(before, after_writer)
        with QualificationReview(self.path) as r:
            self.assertEqual(r.summary(self.session)['counts']['records'], 206)
        self.assertEqual(after_writer, hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_citations_checkpoint_and_session_isolation(self):
        with Memory(self.path) as m:
            e = self.event(action='FAIL')
            m.append(e, self.stream, 1)
            finding = m.save_investigation(m.investigate(self.session))
        with QualificationReview(self.path) as r:
            saved = r.page(self.session)[1]
            result = r.citations(self.session, saved['event']['event_id'])
            self.assertTrue(result['checkpoint'].startswith('MATCHES'))
            self.assertEqual(result['references'][0]['record']['event']['event_id'], e['event_id'])
            self.assertIsNone(r.resolve(str(uuid4()), e['event_id']))
            self.assertIsNone(r.resolve(self.session, str(uuid4())))
            self.assertEqual(finding['arrival'], saved['arrival'])

    def test_missing_citations_and_contradictory_checkpoint(self):
        with Memory(self.path) as m:
            m.append(self.event(status='inferred', interpretation_level='inference',
                metadata=dict(evidence_ids=[str(uuid4()), 'bad-reference'], through_arrival=12, checkpoint='0'*64)),
                self.stream, 1, origin='local-investigator')
        with QualificationReview(self.path) as r:
            s = r.summary(self.session)
            self.assertEqual(s['counts']['missing_citations'], 2)
            self.assertEqual(s['counts']['checkpoint_mismatches'], 1)
            self.assertIn('do not prove causation', summary_text(s))

    def test_conflicting_public_outcomes_remain_claims(self):
        with Memory(self.path) as m:
            for seq, code in enumerate([0, 1], 1):
                m.append(self.event(source='codex', category='command', status='observed', interpretation_level='observation',
                    metadata=dict(codex_event='item.completed', item_id='item_1', exit_code=code)), self.stream, seq)
        with QualificationReview(self.path) as r:
            s = r.summary(self.session)
            self.assertEqual(s['counts']['contradictory_outcome_reports'], 1)
            self.assertEqual(s['classes'], {'AGENT_REPORTED': 2})

    def test_new_turn_item_reuse_is_not_a_contradiction(self):
        with Memory(self.path) as m:
            sequence = 0
            for code in [0, 1]:
                for category, meta in [('agent', dict(codex_event='turn.started')),
                        ('command', dict(codex_event='item.completed', item_id='item_1', exit_code=code))]:
                    sequence += 1
                    m.append(self.event(source='codex', category=category, status='observed',
                        interpretation_level='observation', metadata=meta), self.stream, sequence)
        with QualificationReview(self.path) as r:
            self.assertEqual(r.summary(self.session)['counts'].get('contradictory_outcome_reports', 0), 0)

    def test_integrity_tampering_and_expected_tip_fail_closed(self):
        self.fill(1)
        with QualificationReview(self.path, expected_tip='0'*64) as r:
            self.assertFalse(r.available)
            with self.assertRaises(ValueError):
                r.page(self.session)
        with closing(sqlite3.connect(self.path)) as db:
            with db:
                db.execute("UPDATE records SET fingerprint=?", ('0'*64,))
        with QualificationReview(self.path) as r:
            self.assertFalse(r.integrity['ok'])
            with self.assertRaises(ValueError):
                r.summary(self.session)

    def test_missing_empty_database_and_bounds(self):
        with self.assertRaises(sqlite3.OperationalError):
            QualificationReview(self.path)
        self.assertFalse(self.path.exists())
        self.fill(0)
        with QualificationReview(self.path) as r:
            self.assertEqual(r.sessions(), [])
            self.assertEqual(r.summary(self.session)['counts'], {})
            for limit in [0, 101, True]:
                with self.assertRaises(ValueError):
                    r.page(self.session, limit=limit)

    def test_cancelled_snapshot(self):
        self.fill(1)
        with self.assertRaises(ValueError):
            QualificationReview(self.path, cancelled=lambda: True)

    def test_native_widgets_all_pages_citation_and_shutdown(self):
        self.fill()
        with Memory(self.path) as m:
            m.append(self.event(action='FAIL'), self.stream, 206)
            m.save_investigation(m.investigate(self.session))
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        root = tk.Tk(); root.withdraw()
        window = QualificationWindow(root, self.path, session=self.session)
        def settle():
            deadline = time.monotonic() + 10
            while window.busy and time.monotonic() < deadline:
                root.update(); time.sleep(.01)
            self.assertFalse(window.busy, window.status.get())
        try:
            settle()
            self.assertEqual(len(window.records), 100)
            window.next.invoke(); settle()
            self.assertEqual(window.offset, 100)
            window.next.invoke(); settle()
            self.assertEqual(len(window.records), 7)
            self.assertEqual(str(window.next['state']), 'disabled')
            window.tree.selection_set('207'); root.update(); settle()
            self.assertEqual(len(window.refs), 1)
            window.open_citation()
            self.assertIn('FAIL', window.details.get('1.0', 'end'))
            window.previous.invoke(); settle()
            self.assertEqual(window.offset, 100)
            self.assertIn('207 retained records', window.summary.get('1.0', 'end'))
        finally:
            window.close()
            deadline = time.monotonic() + 5
            while not window.closed and time.monotonic() < deadline:
                root.update(); time.sleep(.01)
            self.assertTrue(window.closed)
            window.worker.join(3)
        self.assertFalse(window.worker.is_alive())
        self.assertEqual(before, hashlib.sha256(self.path.read_bytes()).hexdigest())
