import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from apm.core.controller import Controller
from apm.storage.reader import read_session


class IntegrationTests(unittest.TestCase):
    def test_live_attach_records_changes_and_stop_does_not_kill_specimen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / 'workspace'
            workspace.mkdir()
            script = workspace / 'specimen.py'
            script.write_text('import time\ntime.sleep(25)\n', encoding='utf-8')
            specimen = subprocess.Popen([sys.executable, str(script)], cwd=workspace,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            controller = Controller(workspace, root / 'sessions', specimen.pid)
            try:
                controller.start()
                deadline = time.monotonic() + 5
                while controller.status == 'starting' and time.monotonic() < deadline:
                    time.sleep(.05)
                time.sleep(1)
                (workspace / 'observed.py').write_text('print("hello")\n')
                (root / 'outside.py').write_text('not in scope')
                time.sleep(2.8)
                controller.stop()
                self.assertTrue(controller.wait(15))
                self.assertEqual(controller.status, 'stopped', controller.error)
                self.assertIsNone(specimen.poll(), 'Stopping observation must never kill attached process')
                info, events, warnings = read_session(controller.session_path)
                self.assertFalse(warnings)
                self.assertTrue(any(e.category == 'system' for e in events))
                self.assertTrue(any(e.category == 'process' and e.metadata.get('pid') == specimen.pid for e in events))
                self.assertTrue(any(e.category in ('file', 'filesystem') and 'observed.py' in e.target for e in events))
                self.assertFalse(any('outside.py' in e.target for e in events))
                self.assertFalse(any(e.action == 'READ' for e in events))
                self.assertEqual(info['dropped_events'], 0)
                with patch('subprocess.Popen', side_effect=AssertionError('Replay must not execute')):
                    self.assertEqual(len(read_session(controller.session_path)[1]), len(events))
            finally:
                controller.stop()
                controller.wait(15)
                specimen.terminate()
                specimen.wait(timeout=5)

    def test_demo_is_durable_and_every_action_explicitly_synthetic(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = Controller(Path(tmp), Path(tmp) / 'sessions', demo=True)
            controller.start()
            time.sleep(.9)
            controller.stop()
            self.assertTrue(controller.wait(5))
            _, events, _ = read_session(controller.session_path)
            self.assertGreater(len(events), 2)
            self.assertTrue(all(e.status == 'synthetic' and e.interpretation_level == 'synthetic' for e in events))


if __name__ == '__main__': unittest.main()
