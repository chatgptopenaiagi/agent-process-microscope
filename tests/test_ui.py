from collections import deque
from pathlib import Path
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from apm.ui.main_window import APMWindow, controller_factory, session_reader
from apm.ui.model import LENSES, TimelineBuffer, bytes_text, event_lens, matches


def event(number=1, **overrides):
    return dict(schema_version="1.0", event_id=f"e-{number}", session_id="synthetic-session",
                timestamp=f"2026-09-27T09:00:{number % 60:02d}+00:00", agent_id="demo-agent",
                source="synthetic-fixture", category="process", action="START", target="fixture.py",
                status="synthetic", confidence=1.0, interpretation_level="synthetic",
                raw_reference="metadata/evidence-1", metadata={}) | overrides


class BufferTests(unittest.TestCase):
    def test_bounded_buffer_evicts_oldest_and_filter_does_not_delete(self):
        model = TimelineBuffer(3)
        for number in range(5):
            model.add(event(number, category="file" if number % 2 else "process"))
        self.assertEqual([row[1]["event_id"] for row in model.rows], ["e-2", "e-3", "e-4"])
        self.assertEqual(len(model.filtered(category="file")), 1)
        self.assertEqual(len(model), 3)
        self.assertEqual(model.filtered(search="FIXTURE.PY"), list(model.rows))
        self.assertFalse(matches(event(), status="observed"))

    def test_four_semantic_lenses_preserve_event_evidence(self):
        value = event()
        outputs = [event_lens(value, lens) for lens in LENSES]
        self.assertEqual(len(set(outputs)), 4)
        self.assertIn("not live activity", outputs[0])
        self.assertIn("synthetic-fixture", outputs[1])
        self.assertIn("metadata/evidence-1", outputs[2])
        self.assertIn('"event_id": "e-1"', outputs[3])
        self.assertEqual(value["metadata"], {})

    def test_invalid_limits_and_unavailable_measurements_are_explicit(self):
        with self.assertRaises(ValueError):
            TimelineBuffer(2001)
        self.assertEqual(bytes_text(None), "Unavailable")
        self.assertEqual(bytes_text(1024, True), "1.0 KiB/s")


class FakeController:
    instances = []

    def __init__(self, workspace, sessions_root, pid=None, demo=False):
        self.workspace, self.pid, self.demo = workspace, pid, demo
        self.session_path = sessions_root / "fake-session"
        self.status = "ready"
        self.session_info = {"session_id": "fake-session"}
        self.dropped_count = 0
        self.current_state = None
        self.events = deque()
        self.start_count = self.stop_count = self.wait_count = 0
        self.error = None
        self.instances.append(self)

    def start(self):
        self.start_count += 1
        self.status = "recording"

    def stop(self):
        self.stop_count += 1
        self.status = "stopping"

    def wait(self, timeout=15):
        self.wait_count += 1
        self.status = "error" if self.error else "stopped"
        return True

    def drain(self, limit=200):
        return [self.events.popleft() for _ in range(min(limit, len(self.events)))]


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temporary.cleanup)
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"Native Tk unavailable: {error}")
        self.root.withdraw()
        FakeController.instances.clear()
        self.read_calls = []

        def reader(path):
            self.read_calls.append(path)
            if FakeController.instances:
                self.assertEqual(FakeController.instances[-1].status, "stopped")
                self.assertGreater(FakeController.instances[-1].wait_count, 0)
            return {"session_id": "replay-fixture"}, [event(1), event(2)], []

        self.app = APMWindow(self.root, self.temporary.name, Path(self.temporary.name) / "sessions",
                             demo=True, controller_factory=FakeController, session_reader=reader)
        self.addCleanup(self.cleanup_window)

    def cleanup_window(self):
        try:
            if self.app.controller:
                self.app.controller.stop()
                self.app.controller.wait()
            self.app._active = self.app._starting = self.app._stopping = False
            self.app.close()
        except tk.TclError:
            pass

    def pump_until(self, predicate, timeout=3):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.root.update()
            if predicate():
                return
            time.sleep(.01)
        self.fail("UI did not reach the expected bounded state")

    def start(self):
        self.app.start_observation()
        self.pump_until(lambda: self.app._active)
        return self.app.controller

    def test_creation_does_not_start_observation(self):
        self.root.update()
        self.assertEqual(FakeController.instances, [])
        self.assertIsNone(self.app.controller)
        self.assertEqual(self.app.header_var.get(), "READY TO OBSERVE")

    def test_pause_retains_collection_and_clear_only_changes_view(self):
        controller = self.start()
        controller.events.append(event())
        self.pump_until(lambda: len(self.app.buffer) == 1)
        self.app.paused_var.set(True)
        self.app.toggle_pause()
        controller.events.append(event(2))
        self.pump_until(lambda: len(self.app.buffer) == 2)
        self.assertEqual(len(self.app.tree.get_children()), 1)
        self.assertEqual(controller.stop_count, 0)
        self.app.paused_var.set(False)
        self.app.toggle_pause()
        self.assertEqual(len(self.app.tree.get_children()), 2)
        self.app.clear_view()
        self.assertEqual(len(self.app.buffer), 0)
        self.assertEqual(controller.stop_count, 0)
        self.assertTrue(self.app._active)

    def test_duplicate_start_is_rejected_and_stop_waits_for_flush(self):
        controller = self.start()
        self.app.start_observation()
        self.assertEqual(len(FakeController.instances), 1)
        self.app.stop_observation()
        self.pump_until(lambda: not self.app._active)
        self.assertEqual(controller.stop_count, 1)
        self.assertEqual(controller.wait_count, 1)

    def test_replay_stops_and_flushes_observation_then_stays_passive(self):
        controller = self.start()
        self.app.open_session(Path(self.temporary.name) / "recorded")
        self.pump_until(lambda: self.app._replay_mode)
        self.assertEqual(controller.status, "stopped")
        self.assertEqual(len(self.read_calls), 1)
        self.assertEqual(len(FakeController.instances), 1)
        self.assertEqual(self.app.header_var.get(), "REPLAY PASSIVE")
        self.assertEqual(len(self.app.buffer), 0)
        self.app.speed_var.set("Instant")
        self.app.toggle_replay()
        self.pump_until(lambda: self.app._replay_index == 2)
        self.assertEqual(len(self.app.buffer), 2)
        self.app.start_observation()
        self.assertEqual(len(FakeController.instances), 1)
        self.app.stop_replay()
        self.assertEqual(self.app._replay_index, 0)
        self.assertEqual(len(self.app._replay_events), 2)

    def test_filters_and_selection_keep_all_evidence_magnifications(self):
        self.app._consume([event(1), event(2, category="file", target="math.py")])
        self.app.category_var.set("file")
        self.app._apply_filter()
        self.assertEqual(len(self.app.buffer), 2)
        rows = self.app.tree.get_children()
        self.assertEqual(len(rows), 1)
        self.app.tree.selection_set(rows[0])
        self.app._selection_changed()
        for lens in LENSES:
            self.app.lens_var.set(lens)
            self.app._show_details()
            self.assertIn("math.py", self.app.details.get("1.0", "end"))

    def test_background_controller_failure_is_prominent(self):
        controller = self.start()
        controller.error = "Fixture recorder error"
        controller.status = "error"
        self.pump_until(lambda: not self.app._active)
        self.assertEqual(self.app.header_var.get(), "OBSERVATION ERROR")
        self.assertIn("Fixture recorder error", self.app.footer_var.get())

    def test_completed_demo_waits_for_flush_and_stays_labelled_synthetic(self):
        controller = self.start()
        controller.status = "stopped"
        self.pump_until(lambda: not self.app._active)
        self.assertEqual(controller.wait_count, 1)
        self.assertEqual(self.app.header_var.get(), "DEMO SYNTHETIC")

    def test_paused_visible_evidence_survives_bounded_buffer_rollover(self):
        self.app.buffer = TimelineBuffer(2)
        self.app._consume([event(1), event(2)])
        original_row = self.app.tree.get_children()[0]
        self.app.paused_var.set(True)
        self.app._consume([event(3), event(4), event(5)])
        self.assertEqual(len(self.app.buffer), 2)
        self.assertEqual(len(self.app.tree.get_children()), 2)
        self.app.tree.selection_set(original_row)
        self.app._selection_changed()
        self.assertEqual(self.app._selected['event_id'], 'e-1')
        self.app.paused_var.set(False)
        self.app.toggle_pause()
        self.assertEqual(len(self.app._display_events), 2)
        self.assertEqual([item['event_id'] for item in self.app._display_events.values()], ['e-4', 'e-5'])

    def test_real_synthetic_controller_records_flushes_and_replays_passively(self):
        self.app._factory = controller_factory
        self.app._reader = session_reader
        controller = self.start()
        self.pump_until(lambda: not self.app._active, timeout=20)
        self.assertEqual(controller.status, "stopped")
        self.assertTrue((controller.session_path / "session.json").is_file())
        self.assertTrue((controller.session_path / "events.jsonl").is_file())
        self.assertGreater(len(self.app.buffer), 3)
        self.assertEqual(self.app.header_var.get(), "DEMO SYNTHETIC")
        recorded_count = len(self.app.buffer)

        def forbidden_new_controller(**kwargs):
            self.fail("Passive replay must not create any controller")
        self.app._factory = forbidden_new_controller
        self.app.open_session(controller.session_path)
        self.pump_until(lambda: self.app._replay_mode)
        self.assertEqual(len(self.app._replay_events), recorded_count)
        self.app.speed_var.set("Instant")
        self.app.toggle_replay()
        self.pump_until(lambda: self.app._replay_index == recorded_count)
        self.assertEqual(len(self.app.buffer), recorded_count)
        self.assertEqual(self.app.header_var.get(), "REPLAY PASSIVE")
        self.assertIsNone(self.app.controller)

    def test_replay_duration_uses_recorded_clock_between_events(self):
        self.app._install_replay(({"session_id": "clock-fixture"}, [event(0), event(10)], []), Path(self.temporary.name))
        self.app._replay_playing = True
        self.app._replay_anchor = 100.0
        with patch("apm.ui.main_window.time.monotonic", return_value=103.0):
            self.app._pump_replay()
        self.assertEqual(self.app._replay_index, 1)
        self.assertEqual((self.app._replay_clock - self.app._state_time).total_seconds(), 3)

    def test_replay_reconstructs_same_conservative_state_and_labels_as_live(self):
        from apm.core.state import StateEngine
        events = [event(1, category="process", action="START", metadata={"pid": 7}),
                  event(2, category="file", action="WRITE", target="math.py"),
                  event(3, category="test", action="START", target="unittest"),
                  event(4, category="system", action="SAMPLE")]
        expected = StateEngine()
        for item in events:
            expected.accept(SimpleNamespace(**item))
        self.app._install_replay(({"session_id": "state-fixture"}, events, []), Path(self.temporary.name))
        self.app.speed_var.set("Instant")
        self.app.toggle_replay()
        self.app._pump_replay()
        self.assertEqual(self.app._replay_engine.current.to_dict(), expected.current.to_dict())
        self.assertEqual(self.app.activity_var.get(), "TESTING")
        self.assertEqual(self.app.activity_detail_var.get(), "Recorded · " + expected.current.summary)
        self.assertIn("DEMO / SYNTHETIC", self.app.activity_detail_var.get())
        self.assertEqual(FakeController.instances, [])
        self.app.stop_replay()
        self.assertEqual(self.app._replay_engine.current.state, "IDLE")
        self.assertEqual(self.app._replay_engine.current.event_ids, ())

    def test_instant_replay_accepts_early_state_outside_visible_buffer(self):
        events = [event(0, status="observed", metadata={"pid": 7})]
        events.extend(event(number, category="system", action="SAMPLE", status="observed",
                            timestamp="2026-09-27T09:00:01+00:00") for number in range(1, 2105))
        self.app._install_replay(({"session_id": "long-fixture"}, events, []), Path(self.temporary.name))
        self.app.speed_var.set("Instant")
        self.app.toggle_replay()
        self.app._pump_replay()
        self.assertEqual(self.app._replay_index, 200)
        while self.app._replay_playing:
            self.app._pump_replay()
        self.assertEqual(self.app._replay_index, 2105)
        self.assertEqual(len(self.app.buffer), 2000)
        self.assertEqual(self.app.activity_var.get(), "EXECUTING")
        self.assertEqual(self.app._replay_engine.current.event_ids, ("e-0",))
        self.assertEqual(FakeController.instances, [])


if __name__ == "__main__":
    unittest.main()
