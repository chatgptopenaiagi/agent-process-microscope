"""Hostile replay input and interrupted-storage regressions; synthetic evidence only."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from apm.core.events import Event
from apm.storage.reader import read_session
from apm.storage.recorder import Recorder


class ReaderSecurityTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parents[1] / "cache"
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.session_id = str(uuid4())
        self.info = {"schema_version": "1.0", "session_id": self.session_id, "status": "stopped"}

    def event(self, **changes):
        record = Event(session_id=self.session_id, agent_id="test", source="synthetic-fixture",
                       category="command", action="STOP", target="never execute this").to_dict()
        return record | changes

    def write(self, *, info=None, records=None):
        (self.root / "session.json").write_text(json.dumps(self.info if info is None else info), encoding="utf-8")
        (self.root / "events.jsonl").write_text("".join(json.dumps(row) + "\n" for row in (records or [])), encoding="utf-8")

    def test_nonobject_session_metadata_is_rejected_without_attribute_error(self):
        for value in ([], "CANARY", 123, False):
            with self.subTest(value=value):
                self.write(info=value)
                with self.assertRaises(ValueError):
                    read_session(self.root)
        (self.root / "session.json").write_text("null", encoding="utf-8")
        with self.assertRaises(ValueError):
            read_session(self.root)

    def test_wrong_event_field_types_fail_closed(self):
        for field, value in (("timestamp", []), ("event_id", 7), ("session_id", []),
                             ("category", {}), ("raw_reference", {"unexpected": "CANARY"}),
                             ("confidence", True), ("target", ["CANARY"])):
            with self.subTest(field=field):
                self.write(records=[self.event(**{field: value})])
                with self.assertRaises(ValueError) as caught:
                    read_session(self.root)
                self.assertNotIn("CANARY", str(caught.exception))

    def test_empty_session_still_requires_a_valid_uuid(self):
        for value in (None, [], 123, "", "CANARY invalid uuid"):
            with self.subTest(value=value):
                self.write(info=self.info | {"session_id": value})
                with self.assertRaisesRegex(ValueError, "UUID") as caught:
                    read_session(self.root)
                self.assertNotIn("CANARY", str(caught.exception))
        self.write(info={"schema_version": "1.0"})
        with self.assertRaisesRegex(ValueError, "UUID"):
            read_session(self.root)

    def test_duplicate_keys_nonfinite_numbers_and_excessive_nesting_rejected(self):
        self.write()
        for raw in ('{"schema_version":"1.0","schema_version":"other"}',
                    '{"schema_version":"1.0","extra":NaN}', '[' * 1500 + '0' + ']' * 1500):
            with self.subTest(raw=raw[:60]):
                (self.root / "session.json").write_text(raw, encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_session(self.root)
        self.write()
        (self.root / "events.jsonl").write_text('[' * 1500 + '0' + ']' * 1500 + '\n', encoding="utf-8")
        with self.assertRaises(ValueError):
            read_session(self.root)

    def test_timezone_sort_uses_actual_time_and_preserves_ties(self):
        later = self.event(timestamp="2026-09-27T08:00:00Z")
        earlier = self.event(timestamp="2026-09-27T09:00:00+02:00")
        tie = self.event(timestamp="2026-09-27T07:00:00Z")
        self.write(records=[later, earlier, tie])
        _, events, _ = read_session(self.root)
        self.assertEqual([event.event_id for event in events], [earlier["event_id"], tie["event_id"], later["event_id"]])

    def test_metadata_growth_after_stat_is_still_bounded(self):
        self.write()
        target = self.root / "session.json"
        original_open = Path.open

        def growing_open(path, mode="r", *args, **kwargs):
            if path == target and mode == "rb":
                with original_open(path, "ab") as out:
                    out.write(b"x" * 257)
            return original_open(path, mode, *args, **kwargs)

        with patch("apm.storage.reader.MAX_LINE_BYTES", 256), patch.object(Path, "open", growing_open):
            with self.assertRaisesRegex(ValueError, "metadata too large"):
                read_session(self.root)

    def test_event_growth_after_stat_is_capped_by_total_bytes(self):
        self.write(records=[self.event()])
        target = self.root / "events.jsonl"
        budget = target.stat().st_size + 1
        original_open = Path.open

        def growing_open(path, mode="r", *args, **kwargs):
            if path == target and mode == "rb":
                with original_open(path, "ab") as out:
                    out.write((json.dumps(self.event()) + "\n").encode())
            return original_open(path, mode, *args, **kwargs)

        with patch("apm.storage.reader.MAX_FILE_BYTES", budget), patch.object(Path, "open", growing_open):
            with self.assertRaisesRegex(ValueError, "grew beyond"):
                read_session(self.root)

    def test_forbidden_aliases_redacted_on_replay_and_direct_recording(self):
        private = "CANARY_CONTENT_8564"
        metadata = {name: private for name in ("reasoning_content", "chainOfThought", "aggregatedOutput",
                                               "fileContent", "stdout", "stderr", "analysis")}
        metadata["nested"] = {"apiKey": private}
        self.write(records=[self.event(metadata=metadata)])
        with patch("subprocess.Popen", side_effect=AssertionError("replay cannot launch")), \
                patch("os.system", side_effect=AssertionError("replay cannot execute")):
            _, events, _ = read_session(self.root)
        self.assertNotIn(private, json.dumps(events[0].to_dict()))
        # Defense in depth when a caller bypasses Normalizer and constructs Event.
        recorder = Recorder(self.root / "recorded", self.info)
        self.addCleanup(lambda: recorder.close({}))
        recorder.record(Event(**self.event(metadata=metadata)))
        recorder.close({"status": "stopped"})
        self.assertNotIn(private, (recorder.path / "events.jsonl").read_text())

    def test_storage_handles_close_after_checkpoint_or_fsync_failure(self):
        for failing_method in ("flush", "checkpoint"):
            with self.subTest(failing_method=failing_method):
                recorder = Recorder(self.root / failing_method, self.info)
                with patch.object(recorder, failing_method, side_effect=OSError("simulated storage failure")):
                    with self.assertRaises(OSError):
                        recorder.close({"status": "stopped"})
                self.assertTrue(recorder.events.closed)
                self.assertTrue(recorder.states.closed)
                self.assertTrue(recorder.closed)

    def test_second_stream_closes_even_when_first_close_raises(self):
        recorder = Recorder(self.root / "close-failure", self.info)
        original_stream = recorder.events
        self.addCleanup(original_stream.close)
        self.addCleanup(recorder.states.close)

        class FailingClose:
            def __getattr__(self, name):
                return getattr(original_stream, name)

            def close(self):
                # Real buffered close can release its handle and still raise on
                # a flush failure. The other stream must always get cleanup.
                original_stream.close()
                raise OSError("simulated close-time flush failure")

        recorder.events = FailingClose()
        with self.assertRaisesRegex(OSError, "close-time"):
            recorder.close({"status": "stopped"})
        self.assertTrue(original_stream.closed)
        self.assertTrue(recorder.states.closed)
        self.assertTrue(recorder.closed)


if __name__ == "__main__":
    unittest.main()
