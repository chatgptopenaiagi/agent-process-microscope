"""Synthetic lifecycle tests; standard unittest includes the fresh-process probe."""
from pathlib import Path
import subprocess
import sys
import threading
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from fixture_support import SyntheticDirectory
from apm.ui.holmes_window import HolmesWindow
from apm.ui.main_window import APMWindow
from apm.ui.memory_window import MemoryWindow
from apm.ui.qualification_window import QualificationWindow
from apm.ui.ownership import run_operation


def pump(root, predicate):
    deadline = time.monotonic() + 10
    while not predicate() and time.monotonic() < deadline:
        root.update(); time.sleep(.005)
    if not predicate():
        raise AssertionError('GUI lifecycle did not complete within the bound')


class TkOwnershipTests(unittest.TestCase):
    def test_successful_exit_does_not_hide_shutdown_errors(self):
        from scripts.ci_checks import inspect_test_log
        log = 'Ran 2 tests in 0.1s\n\nOK\n'
        result = inspect_test_log(log)
        self.assertTrue(result['unittest_ok'])
        self.assertEqual(result['test_count'], 2)
        self.assertEqual(result['shutdown_diagnostics'], [])
        self.assertTrue(inspect_test_log(log, expected_tests=2)['unittest_ok'])
        self.assertFalse(inspect_test_log(log, expected_tests=3)['unittest_ok'])
        for incomplete in ('OK\n', 'Ran 2 tests in 0.1s\n',
                           'Ran 0 tests in 0.1s\n\nOK\n', log + log,
                           log + 'unexpected termination', log.replace('OK', 'OK (skipped=1)')):
            self.assertFalse(inspect_test_log(incomplete)['unittest_ok'], incomplete)
        with self.assertRaises(ValueError):
            inspect_test_log(log, expected_tests=0)
        for warning in ('RuntimeError: main thread is not in main loop',
                        'Tcl_AsyncDelete: async handler deleted by the wrong thread',
                        'RuntimeWarning: the Tcl interpreter is leaked',
                        'Exception ignored in: <function Variable.__del__>'):
            self.assertTrue(inspect_test_log(log + warning)['shutdown_diagnostics'])
            self.assertFalse(inspect_test_log(log + warning)['unittest_ok'])

    def test_failed_outcomes_never_transport_exceptions(self):
        def rejected(): raise PermissionError('private payload must not cross')
        result = run_operation(rejected)
        self.assertEqual(result.error, 'PermissionError')
        self.assertIsNone(result.value)
        self.assertNotIn('private', repr(result))

    def test_sequential_error_paths_and_worker_gc_in_fresh_process(self):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('tk_lifecycle_probe.py'))],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
            timeout=90, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '', 'Shutdown diagnostics must not be hidden: ' + result.stderr)
        self.assertIn('"all_on_owner": true', result.stdout)

    def test_worker_cannot_submit_close_or_create_gui(self):
        with SyntheticDirectory() as name:
            root = tk.Tk(); root.withdraw()
            window = HolmesWindow(root, data_root=name)
            errors = []
            def attempt():
                for operation in (window.close, lambda: window.submit(lambda: None, lambda _: None),
                                  lambda: HolmesWindow(root, data_root=name)):
                    try: operation()
                    except RuntimeError as error: errors.append(str(error))
            try:
                worker = threading.Thread(target=attempt); worker.start(); worker.join(3)
                self.assertFalse(worker.is_alive())
                self.assertEqual(len(errors), 3)
                self.assertTrue(all('main GUI thread' in error for error in errors))
                self.assertFalse(window.closed)
            finally:
                window.close()
            window.submit(lambda: self.fail('closed submission ran'), lambda _: None)
            self.assertIsNone(window.future)

    def test_memory_close_waits_for_worker_and_drops_callback(self):
        self.check_query_close(MemoryWindow, 'apm.ui.memory_window.Memory')

    def test_qualification_close_cancels_and_waits_for_worker(self):
        self.check_query_close(QualificationWindow, 'apm.ui.qualification_window.QualificationReview')

    def check_query_close(self, cls, target):
        entered, release = threading.Event(), threading.Event()
        def blocked(*args, **kwargs):
            entered.set()
            if not release.wait(5): raise TimeoutError('synthetic deadline')
            raise ValueError('synthetic rejected database')
        root = tk.Tk(); root.withdraw()
        with patch(target, side_effect=blocked):
            window = cls(root, Path('synthetic-unopened.sqlite3'))
            try:
                self.assertTrue(entered.wait(3))
                window.close(); window.close()
                self.assertTrue(window.closing)
                self.assertFalse(window.closed)
                self.assertTrue(root.winfo_exists())
                release.set()
                pump(root, lambda: window.closed)
                self.assertFalse(window.worker.is_alive())
                self.assertIsNone(window.callback)
                self.assertTrue(window.results.empty())
            finally:
                release.set()
                window.close()
                pump(root, lambda: window.closed)

    def test_parent_waits_for_child_operation(self):
        entered, release = threading.Event(), threading.Event()
        def operation(): entered.set(); release.wait(5)
        with SyntheticDirectory() as name:
            root = tk.Tk(); root.withdraw()
            parent = APMWindow(root)
            child = HolmesWindow(tk.Toplevel(root), data_root=name)
            parent.children.append(child)
            child.submit(operation, lambda _: self.fail('closing callback ran'))
            try:
                self.assertTrue(entered.wait(3))
                parent.close()
                self.assertFalse(parent.closed)
                release.set()
                pump(root, lambda: parent.closed)
                self.assertTrue(child.closed)
            finally:
                release.set(); parent.close(); pump(root, lambda: parent.closed)

    def test_microscope_waits_for_replay_error_during_close(self):
        entered, release = threading.Event(), threading.Event()
        def reader(path):
            entered.set(); release.wait(5)
            raise ValueError('synthetic malformed recording')
        root = tk.Tk(); root.withdraw()
        window = APMWindow(root, session_reader=reader)
        try:
            window.open_session('synthetic-unopened-recording')
            self.assertTrue(entered.wait(3))
            window.close()
            self.assertFalse(window.closed)
            release.set(); pump(root, lambda: window.closed)
            self.assertFalse(window._loading)
            self.assertTrue(window._messages.empty())
        finally:
            release.set(); window.close(); pump(root, lambda: window.closed)
