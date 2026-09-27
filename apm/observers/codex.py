"""Passive, bounded import of explicitly selected ``codex exec --json`` output.

This is not an app-server client, private rollout reader, or model launcher.
Returned payloads must pass through the central Normalizer before consumption.
"""
from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
from uuid import UUID

from apm.adapters.base import ObserverAdapter


_LIFECYCLE = {
    "thread.started": "START", "turn.started": "START",
    "turn.completed": "STOP", "turn.failed": "FAIL",
    "error": "FAIL",
}
_PHASES = {"item.started": "START", "item.updated": "UPDATE", "item.completed": "STOP"}
_EXCLUDED = {"reasoning", "agent_message", "user_message", "mcp_tool_call", "web_search", "todo_list", "plan", "error"}
_ITEM_ID = re.compile(r"item_[0-9]{1,20}\Z")
_KINDS = {"add", "delete", "update"}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("non-finite number")


class CodexAdapter(ObserverAdapter):
    """Import a finite file snapshot; repeated polls never tail a private session.

    ``done`` becomes true at EOF or a limit. Counters include intentionally
    excluded records. File contents, outputs and unknown fields are never emitted.
    """

    name = "codex"

    def __init__(self, path: Path, *, max_line_bytes: int = 1_048_576,
                 max_file_bytes: int = 64 * 1024 * 1024,
                 max_lines: int = 100_000, batch_size: int = 100):
        if not (all(type(value) is int for value in (max_line_bytes, max_file_bytes, max_lines, batch_size))
                and 128 <= max_line_bytes <= 1_048_576 and 128 <= max_file_bytes <= 64 * 1024 * 1024
                and 1 <= max_lines <= 100_000 and 1 <= batch_size <= 1000):
            raise ValueError("Codex import limits out of range")
        self.path = Path(path)
        self.max_line_bytes, self.max_file_bytes = max_line_bytes, max_file_bytes
        self.max_lines, self.batch_size = max_lines, batch_size
        self.done = False
        self.counters = {"lines": 0, "emitted": 0, "excluded": 0, "unavailable": 0}
        self._stream = None
        self._remaining = 0

    def close(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None
        self.done = True

    def _payload(self, category, action, target, metadata=None, *, unavailable=False):
        meta = {"source_line": self.counters["lines"], "provenance": "imported_codex_report",
                "timestamp_basis": "import_time", **(metadata or {})}
        if unavailable:
            self.counters["unavailable"] += 1
        self.counters["emitted"] += 1
        return {"source": self.name, "category": category, "action": action, "target": target,
                "status": "unavailable" if unavailable else "observed", "confidence": 0.0 if unavailable else 1.0,
                "interpretation_level": "observation", "metadata": meta}

    def _unavailable(self, reason):
        # Do not include input text, exception messages, or unknown type values.
        return self._payload("agent", "UNKNOWN", "Codex JSONL import",
                             {"reason": reason}, unavailable=True)

    def _open(self):
        resolved = self.path.resolve(strict=True)
        parts = {part.casefold() for part in resolved.parts}
        if ".codex" in parts or resolved.name.casefold().startswith("rollout-") or resolved.name.casefold() in {
                "auth.json", "config.toml", "history.jsonl", "session_index.jsonl"}:
            raise ValueError("private Codex source denied")
        if not stat.S_ISREG(resolved.stat().st_mode):
            raise ValueError("regular file required")
        self._stream = resolved.open("rb")
        info = os.fstat(self._stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > self.max_file_bytes:
            raise ValueError("file limit or type rejected")
        self._remaining = info.st_size

    def _translate(self, record):
        if not isinstance(record, dict) or not isinstance(record.get("type"), str):
            return self._unavailable("invalid_event_schema")
        event_type = record["type"]
        if event_type in _LIFECYCLE:
            metadata = {"codex_event": event_type}
            if event_type == "thread.started":
                try:
                    metadata["external_thread_id"] = str(UUID(record["thread_id"]))
                except (KeyError, ValueError, TypeError, AttributeError):
                    return self._unavailable("invalid_thread_id")
            # Error messages and usage are deliberately not copied.
            return self._payload("agent", _LIFECYCLE[event_type], "Codex thread", metadata)
        if event_type not in _PHASES:
            return self._unavailable("unsupported_event_type")
        item = record.get("item")
        if not isinstance(item, dict) or not isinstance(item.get("type"), str):
            return self._unavailable("invalid_item_schema")
        item_type = item["type"]
        if item_type in _EXCLUDED:
            self.counters["excluded"] += 1
            return None
        if item_type not in {"command_execution", "file_change"}:
            return self._unavailable("unsupported_item_type")
        item_id, outcome = item.get("id"), item.get("status")
        if not isinstance(item_id, str) or not _ITEM_ID.fullmatch(item_id):
            return self._unavailable("unsupported_item_id")
        if not isinstance(outcome, str) or outcome not in {"in_progress", "completed", "failed", "declined"}:
            return self._unavailable("unsupported_item_status")
        metadata = {"codex_event": event_type, "item_id": item_id, "reported_status": outcome}
        phase = _PHASES[event_type]
        if item_type == "command_execution":
            command = item.get("command")
            if not isinstance(command, str) or not command or len(command) > 32_768:
                return self._unavailable("invalid_command_metadata")
            exit_code = item.get("exit_code")
            if exit_code is not None:
                if type(exit_code) is not int or not -(2**31) <= exit_code <= 2**32 - 1:
                    return self._unavailable("invalid_exit_code")
                metadata["exit_code"] = exit_code
            # No aggregated_output, stdout, stderr, cwd, env, or arbitrary extras.
            return self._payload("command", phase, command, metadata)
        changes = item.get("changes")
        if not isinstance(changes, list) or not 1 <= len(changes) <= 100:
            return self._unavailable("invalid_file_changes")
        allowed = []
        for change in changes:
            if not isinstance(change, dict):
                return self._unavailable("invalid_file_change")
            path, kind = change.get("path"), change.get("kind")
            if (not isinstance(path, str) or not path or len(path) > 4096
                    or not isinstance(kind, str) or kind not in _KINDS):
                return self._unavailable("invalid_file_change")
            allowed.append({"path": path, "kind": kind})
        metadata["changes"] = allowed
        target = allowed[0]["path"] if len(allowed) == 1 else f"{len(allowed)} file changes"
        action = "UPDATE"
        if phase == "STOP" and outcome == "completed" and len(allowed) == 1:
            action = {"add": "CREATE", "update": "WRITE", "delete": "DELETE"}[allowed[0]["kind"]]
        elif outcome in {"failed", "declined"}:
            action = "FAIL"
        return self._payload("file", action, target, metadata)

    def poll(self) -> list[dict]:
        if self.done:
            return []
        if self._stream is None:
            try:
                self._open()
            except (OSError, ValueError):
                self.close()
                return [self._unavailable("input_unavailable_or_disallowed")]
        result = []
        for _ in range(self.batch_size):
            if self._remaining <= 0:
                self.close()
                break
            if self.counters["lines"] >= self.max_lines:
                result.append(self._unavailable("line_count_limit"))
                self.close()
                break
            try:
                raw = self._stream.readline(min(self.max_line_bytes + 1, self._remaining))
            except OSError:
                result.append(self._unavailable("input_read_failed"))
                self.close()
                break
            self._remaining -= len(raw)
            self.counters["lines"] += 1
            if not raw:
                result.append(self._unavailable("input_truncated_during_import"))
                self.close()
                break
            if len(raw) > self.max_line_bytes:
                result.append(self._unavailable("line_size_limit"))
                self.close()
                break
            if not raw.strip():
                continue
            try:
                text = raw.decode("utf-8-sig" if self.counters["lines"] == 1 else "utf-8")
                record = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
                payload = self._translate(record)
            except (UnicodeError, ValueError, RecursionError):
                payload = self._unavailable("invalid_json_record")
            if payload is not None:
                result.append(payload)
        return result
