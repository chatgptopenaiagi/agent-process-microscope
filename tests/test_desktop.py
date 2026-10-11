"""Public synthetic desktop workflow and installed-path policy checks."""
import hashlib
import json
import os
from pathlib import Path
from fixture_support import SyntheticDirectory
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from apm.paths import user_data_root, sessions_root
from apm.holmes.journal import Journal
from apm.holmes.model import Catalog
from apm.holmes.report import case_report, render_html
from apm.ui.holmes_window import HolmesWindow


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = SyntheticDirectory()
        self.directory = Path(self.temp.name)
        self.root = tk.Tk(); self.root.withdraw()
        self.window = HolmesWindow(self.root, data_root=self.directory / 'user-data', producer_class='SYNTHETIC')

    def tearDown(self):
        if not self.window.closed: self.window.close()
        self.temp.cleanup()

    def wait(self):
        deadline = time.monotonic() + 20
        while self.window.busy and time.monotonic() < deadline:
            self.root.update(); time.sleep(.02)
        self.root.update()
        self.assertFalse(self.window.busy)
        self.assertEqual(self.window.operation_status, 'PASS', self.window.operation_error)

    def test_welcome_has_no_side_effects_and_keyboard_navigation(self):
        w = self.window
        self.assertFalse(w.data_root.exists())
        self.assertIsNone(w.path)
        self.assertEqual(w.catalog.summaries(), [])
        self.assertEqual(w.notebook.select(), str(w.pages['welcome']))
        self.assertIn('No observation running', w.banner.get())
        self.assertTrue(self.root.bind('<Control-o>'))
        self.assertTrue(w.claim.bind('<Tab>'))
        self.assertEqual(w.reason.get(), '')  # Placeholder text must never become an assessment.
        w.navigate('review'); self.assertEqual(w.notebook.select(), str(w.pages['review']))

    def test_demo_complete_workflow_close_reopen_and_report(self):
        w = self.window
        w.start_demo(); self.wait()
        self.assertIn('SYNTHETIC', w.banner.get())
        folder, journal_path = w.path.parent, w.path
        sources = [folder / 'synthetic-source.sqlite3', *sorted(folder.glob('*.apmcapsule'))]
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
        shas = [s['sha256'] for s in w.catalog.summaries()]
        self.assertEqual(len(shas), 2)
        for n, role in enumerate(('support', 'contradict')):
            w.capsules.current(n); w.select_capsule(); self.wait()
            rows = w.evidence.get_children()
            w.evidence.selection_set(rows[n]); self.root.update(); w.attach(role)
        w.navigate('hypothesis')
        w.claim.insert('1.0', 'The test failed because of the environment.')
        w.uncertainty.insert('1.0', 'These are synthetic outcomes; no real cause is established.')
        w.alternatives.insert('1.0', 'A source defect\nAn incorrect producer report')
        w.checks.insert('1.0', 'Request an independently captured reference run.')
        w.propose(); self.wait()
        for index in range(2):
            w.citation_choice.current(index); w.resolve_citation(); self.wait()
            self.assertIn('Resolved', w.summary.get('1.0', 'end'))
        w.challenge(); self.wait()
        self.assertIn('INSUFFICIENT EVIDENCE', w.summary.get('1.0', 'end'))
        w.reason.insert(0, 'A fixture assessment, not a causal finding.')
        w.review_state.set('SUPPORTED_WITH_LIMITATIONS'); w.review(); self.wait()
        w.reason.delete(0, 'end'); w.reason.insert(0, 'Correction: conflicting outcomes leave the cause unknown.')
        w.review_state.set('INSUFFICIENT_EVIDENCE'); w.review(True); self.wait()
        self.assertEqual(w.current['revision'], 4)
        w.close()
        self.root = tk.Tk(); self.root.withdraw()
        self.window = w = HolmesWindow(self.root, data_root=self.directory / 'user-data')
        w.open_journal(journal_path); self.wait()
        self.assertEqual(len(w.entries), 4)
        self.assertEqual(w.current['kind'], 'CORRECT')
        for path in sources[1:]: w.open_capsule(path); self.wait()
        w.export(folder / 'investigation.html'); self.wait()
        html = (folder / 'investigation.html').read_text(encoding='utf-8')
        for question in ('What happened?', 'How do we know?', 'What remains unknown?',
                         'What does the evidence suggest?', 'What should the human investigate next?'):
            self.assertIn(question, html)
        self.assertIn('Evidence 1', html); self.assertIn('<details>', html)
        self.assertIn('CORRECT', html)
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
        with Journal(journal_path) as journal:
            self.assertTrue(all(e['execution_authority'] == 'NONE' for e in journal.all_entries()))
            report = case_report(journal, Catalog(), w.case_id)
            self.assertTrue(all(c['status'] == 'UNAVAILABLE' for c in report['citations']))
            self.assertIn('No record contents are inferred', render_html(report))

    def test_rejected_capsule_preserves_case_and_source(self):
        w = self.window
        w.start_demo(); self.wait()
        path = w.path
        bad = self.directory / 'bad.apmcapsule'; bad.write_text('{"execute": "never"}')
        before = bad.read_bytes()
        w.open_capsule(bad)
        deadline = time.monotonic() + 10
        while w.busy and time.monotonic() < deadline: self.root.update(); time.sleep(.02)
        self.assertIn('rejected', w.status.get())
        self.assertEqual(w.path, path); self.assertEqual(bad.read_bytes(), before)
        self.assertEqual(len(w.catalog.summaries()), 2)

    def test_close_finishes_active_operation_before_destroying_tk(self):
        import threading
        ready, release = threading.Event(), threading.Event()
        completed = self.directory / 'completed.txt'
        callbacks = []
        def operation():
            ready.set()
            if not release.wait(5): raise RuntimeError('Fixture release timed out')
            completed.write_text('Synthetic operation completed')
        self.window.submit(operation, lambda _: callbacks.append('called'))
        self.assertTrue(ready.wait(2))
        self.window.close()
        self.assertFalse(self.window.closed)
        self.assertTrue(self.window.closing)
        release.set()
        deadline = time.monotonic() + 10
        while not self.window.closed and time.monotonic() < deadline:
            self.root.update(); time.sleep(.02)
        self.assertTrue(self.window.closed)
        self.assertEqual(self.window.operation_status, 'PASS', self.window.operation_error)
        self.assertTrue(completed.is_file())
        self.assertEqual(callbacks, [])

    def test_permission_failure_has_explicit_outcome_without_private_error_text(self):
        def denied(): raise PermissionError('SYNTHETIC_PRIVATE_PATH')
        self.window.submit(denied, lambda _: self.fail('Failure must not call success callback'))
        deadline = time.monotonic() + 5
        while self.window.busy and time.monotonic() < deadline:
            self.root.update(); time.sleep(.02)
        self.assertEqual(self.window.operation_status, 'FAIL')
        self.assertEqual(self.window.operation_error, 'PermissionError')
        self.assertNotIn('SYNTHETIC_PRIVATE_PATH', self.window.status.get())
        self.assertIn('not accessible', self.window.status.get())
        self.window.submit(lambda: None, lambda _: None); self.wait()


class PathPolicyTests(unittest.TestCase):
    def test_explicit_location_and_installed_default_do_not_depend_on_cwd(self):
        target = Path(__file__).resolve().parent / 'never-created-data'
        self.assertEqual(user_data_root(target), target)
        self.assertFalse(target.exists())
        with patch('apm.paths.sys.platform', 'win32'), patch.dict(os.environ, {'LOCALAPPDATA': str(target)}):
            self.assertEqual(user_data_root(), target / 'APM')
            with patch('apm.paths.sys.frozen', True, create=True):
                self.assertEqual(sessions_root(), target / 'APM' / 'sessions')
        self.assertFalse(target.exists())


if __name__ == '__main__': unittest.main()
