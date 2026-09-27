"""Passive bounded session reader: no adapters, command execution, or writes."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import UUID

from apm.core.events import Event
from apm.security.redaction import sanitize

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_EVENTS = 100_000
MAX_LINE_BYTES = 256 * 1024


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def _constant(_):
    raise ValueError('Non-finite JSON number')


def _decode(value):
    try:
        return json.loads(value, object_pairs_hook=_unique, parse_constant=_constant)
    except (RecursionError, UnicodeError, ValueError):
        raise ValueError('Invalid recording JSON') from None


def read_session(path):
    path = Path(path)
    if path.name == 'session.json':
        path = path.parent
    info_path, events_path = path / 'session.json', path / 'events.jsonl'
    for p in (info_path, events_path):
        if p.is_symlink() or p.resolve().parent != path.resolve():
            raise ValueError('Session files must be within the selected session')
        if p.stat().st_size > MAX_FILE_BYTES:
            raise ValueError('Session exceeds Genesis replay size limit (64 MiB per file)')
    if info_path.stat().st_size > MAX_LINE_BYTES:
        raise ValueError('Session metadata too large')
    with info_path.open('rb') as metadata_stream:
        metadata_bytes = metadata_stream.read(MAX_LINE_BYTES + 1)
    if len(metadata_bytes) > MAX_LINE_BYTES:
        raise ValueError('Session metadata too large')
    info = sanitize(_decode(metadata_bytes))
    if not isinstance(info, dict) or info.get('schema_version') != '1.0':
        raise ValueError('Unsupported session schema')
    if not isinstance(info.get('session_id'), str):
        raise ValueError('Session ID must be a UUID string')
    try:
        UUID(info['session_id'])
    except ValueError:
        raise ValueError('Session ID must be a UUID string') from None
    warnings = []
    if info.get('status') in ('recording', 'starting', 'stopping'):
        warnings.append('Session was open at last checkpoint: it may still be active or have been interrupted.')
    events, seen = [], set()
    total_bytes = 0
    with events_path.open('rb') as stream:
        for number in range(1, MAX_EVENTS + 2):
            raw = stream.readline(MAX_LINE_BYTES + 1)
            total_bytes += len(raw)
            if total_bytes > MAX_FILE_BYTES:
                raise ValueError('Session grew beyond replay byte limit')
            if not raw:
                break
            if number > MAX_EVENTS:
                warnings.append('Replay event limit reached; remaining events omitted.')
                break
            if len(raw) > MAX_LINE_BYTES:
                raise ValueError(f'Event line {number} exceeds size limit')
            try:
                event = Event.from_dict(_decode(raw))
                if event.session_id != info['session_id'] or event.event_id in seen:
                    raise ValueError('Session mismatch or duplicate event ID')
                seen.add(event.event_id)
                events.append(event)
            except (ValueError, TypeError, KeyError, UnicodeError):
                if not raw.endswith(b'\n') and not stream.peek(1):
                    warnings.append(f'Truncated final event at line {number}; preceding events recovered.')
                    break
                raise ValueError(f'Invalid canonical event at line {number}') from None
    # Recording order is the deterministic tie-breaker for equal timestamps.
    events.sort(key=lambda event: datetime.fromisoformat(event.timestamp.replace('Z', '+00:00')))
    return info, events, warnings
