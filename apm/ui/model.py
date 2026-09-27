"""Bounded presentation helpers. This module never observes or executes anything."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import json

MAX_EVENTS = 2000
LENSES = ("Overview", "Activity", "Evidence", "Raw event")


def event_dict(event):
    value = event.to_dict() if hasattr(event, "to_dict") else dict(event)
    if not isinstance(value, dict):
        raise ValueError("Expected a normalized event")
    return value


def timestamp(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result
    except (TypeError, ValueError):
        return None


def clock_text(value):
    moment = timestamp(value)
    return moment.astimezone().strftime("%H:%M:%S.%f")[:-3] if moment else "—"


def duration_text(seconds):
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def bytes_text(value, rate=False):
    if not isinstance(value, (int, float)) or value < 0:
        return "Unavailable"
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    number = float(value)
    for unit in units:
        if number < 1024 or unit == units[-1]:
            return f"{number:,.1f} {unit}" + ("/s" if rate else "")
        number /= 1024


def matches(event, category="All categories", status="All statuses", search=""):
    if category != "All categories" and event.get("category") != category:
        return False
    if status != "All statuses" and event.get("status") != status:
        return False
    query = search.strip().casefold()
    if not query:
        return True
    haystack = " ".join(str(event.get(key, "")) for key in
                        ("timestamp", "agent_id", "source", "category", "action", "target", "status"))
    return query in haystack.casefold()


class TimelineBuffer:
    """View-only ring buffer. Filtering and clearing never touch a recorder."""

    def __init__(self, limit=MAX_EVENTS):
        if not 1 <= limit <= MAX_EVENTS:
            raise ValueError("View limit must be between 1 and 2000")
        self.limit = limit
        self.rows = deque()
        self.serial = 0

    def add(self, event):
        data = event_dict(event)
        self.serial += 1
        key = f"event-{self.serial}"
        expired = self.rows.popleft()[0] if len(self.rows) == self.limit else None
        self.rows.append((key, data))
        return key, data, expired

    def clear(self):
        self.rows.clear()

    def filtered(self, category="All categories", status="All statuses", search=""):
        return [(key, value) for key, value in self.rows if matches(value, category, status, search)]

    def get(self, key):
        return next((event for identity, event in self.rows if identity == key), None)

    def __len__(self):
        return len(self.rows)


def event_lens(event, lens):
    """Four semantic views of one already-redacted event; no new inference."""
    if event is None:
        return "Select an event\n\nChoose a timeline row to inspect its scope, evidence and confidence."
    event = event_dict(event)
    status = str(event.get("status", "unknown"))
    level = str(event.get("interpretation_level", "unknown"))
    confidence = event.get("confidence")
    certainty = f"{confidence:.0%}" if isinstance(confidence, (int, float)) else "Unknown"
    action = str(event.get("action", "UNKNOWN"))
    target = str(event.get("target", ""))
    if lens == "Overview":
        explanation = {
            "observed": "A scoped adapter reported this external event.",
            "inferred": "This is a derived interpretation. Inspect the supporting event references.",
            "synthetic": "This event was generated for the demonstration. It is not live activity.",
            "unavailable": "The requested observation was unavailable. This is not evidence that activity stopped.",
            "unknown": "The available evidence does not establish this event's status.",
        }.get(status, "Inspect the recorded status and evidence before drawing a conclusion.")
        return (f"{action.replace('_', ' ')}\n\n{target or 'No target recorded'}\n\n"
                f"{explanation}\n\nStatus       {status.upper()}\n"
                f"Confidence   {certainty}\nLevel        {level}\n\n"
                "APM presents external actions and labelled interpretations. Private model reasoning is not captured.")
    if lens == "Activity":
        return (f"ACTION  /  {action}\n\nTarget\n{target or 'Not recorded'}\n\n"
                f"Category     {event.get('category', 'unknown')}\n"
                f"Source       {event.get('source', 'unknown')}\n"
                f"Agent        {event.get('agent_id', 'unknown')}\n"
                f"Time         {event.get('timestamp', 'unknown')}\n\n"
                f"Status       {status}\nConfidence   {certainty}\n"
                f"Interpretation level   {level}")
    if lens == "Evidence":
        metadata = json.dumps(event.get("metadata", {}), ensure_ascii=False, indent=2, default=str)
        return _bounded_text(f"Target\n{target or 'Not recorded'}\n\n"
                f"Evidence reference\n{event.get('raw_reference') or 'No reference supplied'}\n\n"
                f"Event ID\n{event.get('event_id', 'unknown')}\n\n"
                f"Session ID\n{event.get('session_id', 'unknown')}\n\n"
                f"Redacted metadata\n{metadata}\n\n"
                "References identify retained evidence; this pane does not open or execute them.")
    if lens == "Raw event":
        return _bounded_text(json.dumps(event, ensure_ascii=False, indent=2, default=str))
    raise ValueError("Unknown magnification")


def _bounded_text(value):
    if len(value) <= 64000:
        return value
    return value[:64000] + "\n\n[Display truncated at 64,000 characters. The recorded event remains unchanged.]"
