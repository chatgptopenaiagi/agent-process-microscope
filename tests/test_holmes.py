from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import tkinter as tk
import unittest
from uuid import uuid4

from apm.holmes.challenge import challenge
from apm.holmes.journal import Journal
from apm.holmes.model import Catalog
from apm.holmes.report import case_report, export_report
from scripts.holmes_demo import fixture, proposed


class HolmesTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1] / 'cache' / ('holmes-test-' + str(uuid4()))
        self.root.mkdir(parents=True); self.addCleanup(shutil.rmtree, self.root)
        self.db, self.case, self.paths = fixture(self.root)
        self.catalog = Catalog(); self.shas = [self.catalog.open(p) for p in self.paths]
        self.value = proposed(self.catalog, self.shas)
        self.path = self.root / 'journal.sqlite3'
        self.journal = Journal.create(self.path); self.addCleanup(self.journal.close)

    def create(self, value=None, request=None):
        return self.journal.propose(self.case, 'Fixture case', 'Investigate without execution.', 'Synthetic reviewer',
            value or self.value, self.catalog, request_id=request or str(uuid4()), producer_class='SYNTHETIC')

    def change(self, h, kind, detail, request=None):
        return self.journal.revise(h['hypothesis_id'], h['revision'], 'Synthetic reviewer', kind, detail,
                                  self.catalog, request_id=request or str(uuid4()), producer_class='SYNTHETIC')

    def test_creation_scoped_citations_and_competing_hypotheses(self):
        a = self.create(); b = self.create(dict(self.value, claim='An environmental restriction explains the report.'))
        self.assertNotEqual(a['hypothesis_id'], b['hypothesis_id'])
        for role in ('support', 'contradict'):
            self.assertTrue(self.catalog.resolve(a['hypothesis'][role][0]))
        self.assertEqual(self.journal.verify()['entries'], 2)
        self.assertEqual(a['execution_authority'], 'NONE')

    def test_invalid_dangling_mismatched_and_unknown_references(self):
        for mutation in [dict(session_id=str(uuid4())), dict(capsule_sha256='f'*64),
                         dict(evidence_id=str(uuid4())), dict(evidence_id='bad'), dict(authority='execute')]:
            value = deepcopy(self.value); value['support'][0].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.create(value)
        value = deepcopy(self.value)
        missing = dict(value['support'][0], evidence_id=str(uuid4()))
        value['support'] = []; value['missing'].append(dict(reference=missing, reason='Explicitly unavailable fixture.'))
        self.assertEqual(self.create(value)['hypothesis']['missing'][-1]['reference'], missing)
        value['missing'][-1]['reference'] = {}
        with self.assertRaises(ValueError): self.create(value)

    def test_idempotent_retry_conflict_and_stale_revision(self):
        request = str(uuid4()); a = self.create(request=request)
        self.assertEqual(a, self.create(request=request))
        with self.assertRaisesRegex(ValueError, 'request_conflict'):
            self.create(dict(self.value, claim='Different claim'), request=request)
        review = dict(state='REJECTED', reason='Not supported.')
        request = str(uuid4()); b = self.change(a, 'REVIEW', review, request)
        self.assertEqual(b, self.change(a, 'REVIEW', review, request))
        with self.assertRaisesRegex(ValueError, 'stale_revision'): self.change(a, 'REVIEW', review)
        self.assertEqual(self.journal.verify()['entries'], 2)

    def test_review_correction_rejection_supersession_and_revision_history(self):
        a = self.create()
        with self.assertRaisesRegex(ValueError, 'no_assessment'): self.change(a, 'CORRECT', dict(state='REJECTED', reason='Invalid correction.'))
        b = self.change(a, 'REVIEW', dict(state='SUPPORTED_WITH_LIMITATIONS', reason='Initial opinion.'))
        c = self.change(b, 'CORRECT', dict(state='INSUFFICIENT_EVIDENCE', reason='Contrary evidence matters.'))
        d = self.change(c, 'REVIEW', dict(state='REJECTED', reason='Withdraw interpretation.'))
        e = self.change(d, 'REVIEW', dict(state='SUPERSEDED', reason='See competing explanation.'))
        f = self.change(e, 'REVISE', dict(hypothesis=dict(self.value, claim='Revised claim.'), reason='New interpretation.'))
        self.assertEqual(f['state'], 'PROPOSED')
        self.assertEqual([e['state'] for e in self.journal.history(a['hypothesis_id'])],
                         ['PROPOSED','SUPPORTED_WITH_LIMITATIONS','INSUFFICIENT_EVIDENCE','REJECTED','SUPERSEDED','PROPOSED'])
        with Journal(self.path) as reopened: self.assertEqual(reopened.latest(a['hypothesis_id']), f)

    def test_deterministic_challenge_reports_conflicts_missing_clocks_and_synthetic(self):
        result = challenge(self.value, self.catalog)
        self.assertEqual(result, challenge(self.value, self.catalog))
        self.assertEqual(result['conclusion'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(result['conflict_groups'], 2)
        self.assertEqual(result['declared_classes'], {'SYNTHETIC': 2})
        self.assertTrue(any('Causal wording' in w for w in result['warnings']))
        self.assertEqual(sum(s['uncited'] for s in result['scope']), 4)
        self.assertEqual(len(challenge(self.value, Catalog())['unavailable']), 2)
        value = deepcopy(self.value); value['contradict'] = value['support']
        self.assertEqual(challenge(value, self.catalog)['contradictory_roles'], 1)

    def test_challenge_persisted_and_verification_never_grants_authority(self):
        a = self.change(self.create(), 'CHALLENGE', {})
        b = self.change(a, 'VERIFICATION', dict(procedure='Declared fixture check only', outcome='REPORTED_PASS',
            limitations='Not independent human authentication.', references=self.value['support']))
        self.assertEqual(b['state'], 'PROPOSED')
        self.assertEqual(b['execution_authority'], 'NONE')
        self.assertEqual(b['producer_class'], 'SYNTHETIC')
        with self.assertRaisesRegex(ValueError, 'human_review_required'):
            self.journal.revise(b['hypothesis_id'], b['revision'], 'Declared agent', 'REVIEW',
                dict(state='SUPPORTED_WITH_LIMITATIONS', reason='Agent assent is not human review.'),
                self.catalog, request_id=str(uuid4()), producer_class='AGENT_REPORTED')
        for kind, detail in [('EXECUTE', {}), ('REVIEW', dict(state='VERIFIED', reason='Claim true')),
            ('REVIEW', dict(state='SUPPORTED_WITH_LIMITATIONS', reason='OK', execute=True)),
            ('REVISE', dict(hypothesis=self.value, reason='OK', authorize=True))]:
            with self.assertRaises(ValueError): self.change(b, kind, detail)

    def test_append_only_backup_and_tampering_detected(self):
        self.create(); integrity = self.journal.verify()
        for sql in ('UPDATE entries SET entity=entity', 'DELETE FROM entries'):
            with self.assertRaises(sqlite3.IntegrityError): self.journal.db.execute(sql)
            self.journal.db.rollback()
        backup = self.root / 'backup.sqlite3'; self.assertEqual(self.journal.backup(backup)['tip'], integrity['tip'])
        with self.assertRaises(FileExistsError): self.journal.backup(backup)
        with self.assertRaises(ValueError): self.journal.verify('f'*64)
        db = sqlite3.connect(backup)
        try:
            with db:
                db.execute('DROP TRIGGER no_update'); db.execute("UPDATE entries SET fingerprint=?", ('f'*64,))
        finally:
            db.close()
        with self.assertRaises(ValueError): Journal(backup)

    def test_interrupted_transaction_recovery(self):
        self.create(); before = self.journal.verify()
        code = "import sqlite3,sys,os; d=sqlite3.connect(sys.argv[1]); d.execute('BEGIN IMMEDIATE'); d.execute(\"INSERT INTO entries VALUES(2,'interrupted','x','x',x'00','x','x')\"); os._exit(7)"
        result = subprocess.run([sys.executable, '-I', '-c', code, str(self.path)], timeout=15,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(result.returncode, 7)
        with Journal(self.path) as reopened: self.assertEqual(reopened.verify(), before)

    def test_no_source_mutation_no_overwrite_or_foreign_database(self):
        paths = [self.db, *self.paths]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        h = self.create(); self.change(h, 'CHALLENGE', {})
        with self.assertRaises(FileExistsError): Journal.create(self.db)
        with self.assertRaises(ValueError): Journal(self.db)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])

    def test_read_snapshot_keeps_verified_tip_and_history_consistent(self):
        a = self.create()
        with Journal(self.path) as other:
            with self.journal.snapshot():
                checked = self.journal.verify()
                other.revise(a['hypothesis_id'], 1, 'Reviewer', 'REVIEW', dict(state='UNDER_REVIEW', reason='New review'),
                             self.catalog, request_id=str(uuid4()))
                self.assertEqual(len(self.journal.all_entries()), checked['entries'])
                self.assertEqual(self.journal.verify()['tip'], checked['tip'])
        self.assertEqual(self.journal.verify()['entries'], 2)

    def test_report_citations_html_escaping_redaction_and_missing_sources(self):
        a = self.create(dict(self.value, claim='<script>alert(1)</script> password=fake-secret'))
        self.change(a, 'REVIEW', dict(state='INSUFFICIENT_EVIDENCE', reason='Need independent evidence.'))
        destination = self.root / 'case.html'
        result = export_report(self.journal, self.catalog, self.case, destination)
        rendered = destination.read_text(encoding='utf-8')
        self.assertEqual(result['citations'], 2)
        self.assertNotIn('<script>', rendered); self.assertNotIn('fake-secret', rendered)
        self.assertIn('&lt;script&gt;', rendered); self.assertIn('href="#citation-', rendered)
        self.assertIn('Content-Security-Policy', rendered)
        with self.assertRaises(FileExistsError): export_report(self.journal, self.catalog, self.case, destination)
        report = case_report(self.journal, Catalog(), self.case)
        self.assertTrue(all(c['status'] == 'UNAVAILABLE' for c in report['citations']))
        self.assertEqual(len(report['history']), 2)

    def test_history_pagination_and_bounds(self):
        a = self.create()
        for n in range(102): a = self.change(a, 'REVIEW', dict(state='UNDER_REVIEW', reason=f'Fixture assessment {n}'))
        page = self.journal.history(); rest = self.journal.history(after=page[-1]['sequence'])
        self.assertEqual([len(page), len(rest)], [100, 3])
        self.assertEqual(self.journal.verify()['entries'], 103)
        for kwargs in [dict(limit=101), dict(after=-1), dict(limit=True)]:
            with self.assertRaises(ValueError): self.journal.history(**kwargs)

    def pattern(self, revision=2):
        return dict(pattern_id=str(uuid4()), version=1, source_review_revision=revision,
            description='Synthetic completed-command nonzero outcome resemblance',
            required=dict(source='codex', category='command', evidence_class='SYNTHETIC', exit_code=1),
            optional=dict(comparison_key='permission-fixture'), counterexamples=[dict(action='START')],
            review_note='Human-style fixture review; no real cause validated.', disposition='ACTIVE')

    def test_patterns_require_review_preserve_versions_and_suspend_after_correction(self):
        from apm.holmes.patterns import retrieve
        a = self.create(); definition = self.pattern(1)
        with self.assertRaisesRegex(ValueError, 'requires_supported_human_review'): self.change(a, 'PATTERN', definition)
        a = self.change(a, 'REVIEW', dict(state='SUPPORTED_WITH_LIMITATIONS', reason='Fixture resemblance only.'))
        definition['source_review_revision'] = a['revision']
        a = self.change(a, 'PATTERN', definition)
        found = retrieve(self.journal, self.catalog)['patterns'][0]
        self.assertEqual(found['matched_records'], 4)
        self.assertEqual(found['version'], 1)
        with self.assertRaisesRegex(ValueError, 'pattern_version'): self.change(a, 'PATTERN', definition)
        definition = dict(definition, version=2, disposition='RETIRED')
        a = self.change(a, 'PATTERN', definition)
        self.assertEqual(retrieve(self.journal, self.catalog)['patterns'], [])
        a = self.change(a, 'PATTERN', dict(definition, version=3, disposition='ACTIVE'))
        self.assertEqual(retrieve(self.journal, self.catalog)['patterns'][0]['version'], 3)
        a = self.change(a, 'CORRECT', dict(state='REJECTED', reason='Historical interpretation withdrawn.'))
        self.assertEqual(retrieve(self.journal, self.catalog)['patterns'][0]['review_status'], 'REASSESSMENT_REQUIRED')
        with self.assertRaisesRegex(ValueError, 'pattern_review_stale'):
            self.change(a, 'PATTERN', dict(definition, version=4, disposition='ACTIVE'))
        # Withdrawal still works with no source capsules available.
        self.journal.revise(a['hypothesis_id'], a['revision'], 'Reviewer', 'PATTERN', dict(definition, version=4), Catalog(), request_id=str(uuid4()))
        self.assertEqual(retrieve(self.journal, self.catalog)['patterns'], [])

    def test_pattern_labeled_false_matches_and_optional_differences(self):
        from apm.holmes.patterns import matches, retrieve, definition
        pattern = self.pattern()
        record = self.catalog.page(self.shas[0])[0]
        fixtures = [(record, True)]
        for field, value in [('source','process'), ('evidence_class','AGENT_REPORTED'), ('category','system')]:
            fixtures.append((dict(record, **{field:value}), False))
        for value in (0, None, 2):
            altered = deepcopy(record); altered['attributes']['exit_code'] = value; fixtures.append((altered, False))
        actual = [matches(pattern['required'], r) for r, _ in fixtures]
        self.assertEqual(actual, [label for _, label in fixtures])  # 1 TP, 6 TN, zero FP/FN in this labeled fixture.
        a = self.change(self.create(), 'REVIEW', dict(state='SUPPORTED_WITH_LIMITATIONS', reason='Fixture only.'))
        pattern['optional'] = dict(comparison_key='different-task')
        self.change(a, 'PATTERN', pattern)
        result = retrieve(self.journal, self.catalog)['patterns'][0]
        self.assertEqual(result['optional_difference_counts'], {'comparison_key': 4})
        for bad in [dict(pattern, required=dict(exit_code=1)), dict(pattern, required=dict(pattern['required'], regex='.*'))]:
            with self.assertRaises(ValueError): definition(bad)

    def test_pattern_counterexamples_exclude_otherwise_matching_records(self):
        from apm.holmes.patterns import retrieve
        a = self.change(self.create(), 'REVIEW', dict(state='SUPPORTED_WITH_LIMITATIONS', reason='Fixture only.'))
        pattern = self.pattern(); pattern['counterexamples'] = [dict(comparison_key='permission-fixture')]
        self.change(a, 'PATTERN', pattern)
        result = retrieve(self.journal, self.catalog)['patterns'][0]
        self.assertEqual(result['matched_records'], 0); self.assertEqual(result['counterexamples_excluded'], 4)

    def test_cooperation_scope_citations_budgets_and_no_consensus_proof(self):
        from apm.holmes.cooperation import synthetic_demo, validate, verify_batch
        demo = synthetic_demo(self.catalog)
        self.assertEqual(len(demo['responses']), 2)
        self.assertEqual(demo['consensus'], 'NOT_PROOF')
        self.assertEqual(demo['execution_authority'], 'NONE')
        message = demo['responses'][0]
        for operation in (lambda m: m.update(execute=True),
                          lambda m: m['limits'].update(max_seconds=999999),
                          lambda m: m['hypothesis']['support'][0].update(evidence_id=str(uuid4())),
                          lambda m: m['scope'][0].update(session_id=str(uuid4())),
                          lambda m: m['hypothesis'].update(support=self.value['contradict'])):
            altered = deepcopy(message); operation(altered)
            with self.assertRaises(ValueError): validate(altered, self.catalog)
        with self.assertRaisesRegex(ValueError, 'duplicate_assessment'):
            verify_batch([message, message], self.catalog)

    def test_fresh_process_acceptance(self):
        result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'scripts/holmes_demo.py'),
            '--worker', str(self.root)], capture_output=True, text=True, timeout=30,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((self.root / 'worker-result.json').read_text())
        self.assertTrue(data['reopened']); self.assertEqual(data['revisions'], 4)

    def test_native_gui_workflow_and_reopen(self):
        from apm.ui.holmes_window import HolmesWindow
        root = tk.Tk(); root.withdraw(); window = HolmesWindow(root, producer_class='SYNTHETIC')
        def wait():
            deadline = time.monotonic() + 20
            while window.busy and time.monotonic() < deadline:
                root.update(); time.sleep(.02)
            root.update(); self.assertFalse(window.busy)
            self.assertNotIn('rejected', window.status.get())
        try:
            gui_path = self.root / 'gui.sqlite3'; window.open_journal(gui_path, create=True); wait()
            for role, path in zip(('support', 'contradict'), self.paths):
                window.open_capsule(path); wait()
                rows = window.evidence.get_children(); window.evidence.selection_set(rows[0]); root.update()
                window.attach(role)
            window.claim.insert('1.0', self.value['claim']); window.uncertainty.insert('1.0', self.value['uncertainty'])
            window.alternatives.insert('1.0', 'Environmental restriction')
            window.propose(); wait(); self.assertEqual(window.current['revision'], 1)
            window.citation_choice.current(0); window.resolve_citation(); wait()
            self.assertIn('Resolved', window.summary.get('1.0','end'))
            window.challenge(); wait(); self.assertIn('INSUFFICIENT EVIDENCE', window.summary.get('1.0','end'))
            window.review_state.set('SUPPORTED_WITH_LIMITATIONS'); window.review(); wait()
            window.review_state.set('INSUFFICIENT_EVIDENCE'); window.review(True); wait()
            self.assertEqual(window.current['revision'], 4)
            window.export(self.root / 'gui.html'); wait(); self.assertTrue((self.root / 'gui.html').exists())
            window.open_journal(gui_path); wait(); self.assertEqual(len(window.history.get_children()), 4)
            last = window.history.get_children()[-1]; window.history.selection_set(last); root.update()
            self.assertIn('CORRECT', window.history_summary.get('1.0','end'))
            # Exercise pagination on an additional bounded synthetic capsule.
            folder = self.root / 'large'; folder.mkdir()
            _, _, paths = fixture(folder, count=105)
            window.open_capsule(paths[0]); wait(); self.assertEqual(len(window.evidence.get_children()), 100)
            window.next_page(); wait(); self.assertEqual(len(window.evidence.get_children()), 5)
            window.previous_page(); wait(); self.assertEqual(len(window.evidence.get_children()), 100)
        finally:
            window.close()
        self.assertTrue(window.closed)
        import threading
        deadline = time.monotonic() + 5
        while any(t.name.startswith('APM-Holmes') for t in threading.enumerate()) and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertFalse(any(t.name.startswith('APM-Holmes') for t in threading.enumerate()))


if __name__ == '__main__': unittest.main()
