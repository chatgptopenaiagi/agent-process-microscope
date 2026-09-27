import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from apm.core.events import Normalizer
from apm.observers.codex import CodexAdapter


class CodexImportTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parents[1] / "cache"
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.normalizer = Normalizer(str(uuid4()), "codex-import")

    def import_records(self, records, **limits):
        path = self.root / "selected-export.jsonl"
        path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
        adapter = CodexAdapter(path, **limits)
        self.addCleanup(adapter.close)
        result = []
        while not adapter.done:
            result.extend(adapter.poll())
        return result, adapter

    @staticmethod
    def item(kind="command_execution", **fields):
        return {"type": "item.completed", "item": {"id": "item_1", "type": kind,
                "status": "completed", "command": "python -m unittest", "exit_code": 0, **fields}}

    def test_lifecycle_commands_and_file_changes_are_passive_canonical_events(self):
        thread = str(uuid4())
        records = [{"type": "thread.started", "thread_id": thread}, {"type": "turn.started"},
                   {"type": "item.started", "item": {"type": "command_execution", "id": "item_1",
                    "command": "python -m unittest", "status": "in_progress"}}, self.item(),
                   self.item("file_change", changes=[{"path": "tests/test_demo.py", "kind": "add"}]),
                   {"type": "turn.completed"}]
        with patch("subprocess.Popen", side_effect=AssertionError("import must not spawn")), \
                patch("os.system", side_effect=AssertionError("import must not execute")):
            payloads, adapter = self.import_records(records, batch_size=2)
        events = [self.normalizer.normalize(payload) for payload in payloads]
        self.assertEqual([e.action for e in events], ["START", "START", "START", "STOP", "CREATE", "STOP"])
        self.assertEqual(events[0].metadata["external_thread_id"], thread)
        self.assertEqual(events[3].metadata["exit_code"], 0)
        self.assertEqual(events[4].metadata["changes"], [{"path": "tests/test_demo.py", "kind": "add"}])
        self.assertTrue(all(e.metadata["provenance"] == "imported_codex_report" for e in events))
        self.assertEqual(adapter.poll(), [])

    def test_reasoning_messages_outputs_diffs_and_unknown_payloads_never_escape(self):
        secret = "CANARY_PRIVATE_CONTENT_4927"
        records = [self.item("reasoning", text=secret, summary=[secret]),
                   self.item("agent_message", text=secret), self.item("mcp_tool_call", arguments=secret),
                   self.item(aggregated_output=secret, stdout=secret, stderr=secret, env={"PRIVATE": secret}),
                   self.item("file_change", changes=[{"path": "a.py", "kind": "update", "diff": secret}]),
                   {"type": "turn.failed", "error": {"message": secret}},
                   {"type": secret, "payload": secret}, self.item(secret, arbitrary=secret)]
        payloads, adapter = self.import_records(records)
        encoded = json.dumps(payloads)
        self.assertNotIn(secret, encoded)
        for field in ("aggregated_output", "stdout", "stderr", "diff", "arguments", "summary"):
            self.assertNotIn('"' + field + '"', encoded)
        self.assertEqual(adapter.counters["excluded"], 3)
        self.assertEqual(adapter.counters["unavailable"], 2)

    def test_central_normalization_redacts_allowlisted_command_metadata(self):
        payloads, _ = self.import_records([self.item(command='tool --api-key fake-command-secret --password "fake password"')])
        event = self.normalizer.normalize(payloads[0])
        persisted = json.dumps(event.to_dict())
        self.assertNotIn("fake-command-secret", persisted)
        self.assertNotIn("fake password", persisted)
        self.assertIn("[REDACTED]", persisted)

    def test_malformed_json_and_schema_fail_closed_without_original_text(self):
        path = self.root / "malformed.jsonl"
        path.write_bytes(b'{"type":"error","type":"CANARY"}\n'
                         b'{"type": ["CANARY"]}\n'
                         b'{"type":"item.completed","item":{"type":"command_execution","id":[]}}\n'
                         b'{"type":"turn.failed","unused":NaN}\n'
                         b'\xff\n{ "private": "CANARY')
        adapter = CodexAdapter(path)
        self.addCleanup(adapter.close)
        payloads = adapter.poll()
        self.assertEqual(len(payloads), 6)
        self.assertTrue(all(p["status"] == "unavailable" for p in payloads))
        self.assertNotIn("CANARY", json.dumps(payloads))

    def test_line_file_and_record_count_limits_are_explicit(self):
        path = self.root / "large.jsonl"
        path.write_bytes(b'x' * 129 + b'\n' + b'{"type":"turn.started"}\n')
        adapter = CodexAdapter(path, max_line_bytes=128)
        self.assertEqual(adapter.poll()[0]["metadata"]["reason"], "line_size_limit")
        self.assertTrue(adapter.done)
        adapter = CodexAdapter(path, max_file_bytes=128)
        self.assertEqual(adapter.poll()[0]["status"], "unavailable")
        self.assertTrue(adapter.done)
        payloads, adapter = self.import_records([{"type": "turn.started"}] * 3, max_lines=2)
        self.assertEqual(len(payloads), 3)
        self.assertEqual(payloads[-1]["metadata"]["reason"], "line_count_limit")

    def test_snapshot_does_not_read_appended_records_or_modify_input(self):
        path = self.root / "snapshot.jsonl"
        original = b'{"type":"turn.started"}\n' * 2
        path.write_bytes(original)
        adapter = CodexAdapter(path, batch_size=1)
        self.addCleanup(adapter.close)
        result = adapter.poll()
        with path.open("ab") as stream:
            stream.write(b'{"type":"turn.failed"}\n')
        while not adapter.done:
            result.extend(adapter.poll())
        self.assertEqual([p["action"] for p in result], ["START", "START"])
        self.assertEqual(path.read_bytes(), original + b'{"type":"turn.failed"}\n')

    def test_private_codex_paths_denied_before_content_read(self):
        private = self.root / ".codex"
        private.mkdir()
        for path in (private / "selected.jsonl", self.root / "rollout-example.jsonl", self.root / "auth.json"):
            path.write_text("CANARY private data", encoding="utf-8")
            with patch.object(Path, "open", side_effect=AssertionError("must reject before reading")):
                adapter = CodexAdapter(path)
                result = adapter.poll()
            self.assertEqual(result[0]["status"], "unavailable")
            self.assertTrue(adapter.done)

    def test_file_failure_is_not_reported_as_successful_write(self):
        payloads, _ = self.import_records([self.item("file_change", status="failed",
                                                   changes=[{"path": "demo.py", "kind": "update"}])])
        self.assertEqual(payloads[0]["action"], "FAIL")


if __name__ == "__main__":
    unittest.main()
