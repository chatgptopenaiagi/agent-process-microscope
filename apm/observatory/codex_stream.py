"""Opt-in stdin feed of public exec JSONL. Never discovers private histories."""
from __future__ import annotations

import json
from apm.observers.codex import CodexAdapter, _unique_object, _reject_constant


class CodexStream(CodexAdapter):
    def __init__(self):
        # Reuse Genesis's strict action allowlist, without opening any file.
        super().__init__('unused')

    def _payload(self, category, action, target, metadata=None, *, unavailable=False):
        value = super()._payload(category, action, target, metadata, unavailable=unavailable)
        value['metadata'].update(provenance='codex_exec_stream_report', timestamp_basis='client_receipt_time')
        return value

    def read(self, stream):
        """Caller owns the pipe; 1 MiB/line and 100k lines, then explicit stop."""
        for _ in range(self.max_lines):
            raw = stream.readline(self.max_line_bytes+1)
            if not raw:
                return
            self.counters['lines'] += 1
            if len(raw) > self.max_line_bytes:
                yield self._unavailable('line_size_limit_source_stopped')
                return
            try:
                record = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
                value = self._translate(record)
            except (ValueError, UnicodeError, RecursionError):
                value = self._unavailable('invalid_json_record')
            if value is not None:
                yield value
        yield self._unavailable('line_count_limit_source_stopped')
