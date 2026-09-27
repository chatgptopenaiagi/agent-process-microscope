"""Machine aggregate resource counters; never attributed to a selected agent."""
from __future__ import annotations

import time
from typing import Any

import psutil

from apm.adapters.base import ObserverAdapter, payload


class SystemObserver(ObserverAdapter):
    name = "system"

    def __init__(self) -> None:
        self._closed = False
        self._previous_time: float | None = None
        self._previous_counters: dict[str, int] = {}

    def poll(self) -> list[dict[str, Any]]:
        if self._closed:
            return []
        now = time.monotonic()
        interval = None if self._previous_time is None else now - self._previous_time
        unavailable: dict[str, str] = {}
        metadata: dict[str, Any] = {
            "scope": "system_aggregate", "attribution": "unknown",
            "attribution_limit": "These are whole-machine counters, not the attached agent's usage.",
            "sample_interval_seconds": interval,
            "cpu_percent": None, "ram_total_bytes": None, "ram_available_bytes": None,
            "ram_used_bytes": None, "ram_percent": None,
            "gpu_status": "unavailable", "gpu_reason": "No GPU probe is configured."}
        try:
            cpu = psutil.cpu_percent(interval=None)
            if self._previous_time is not None:
                metadata["cpu_percent"] = cpu
            else:
                unavailable["cpu_percent"] = "first_sample_warmup"
        except (psutil.Error, OSError):
            unavailable["cpu_percent"] = "counter_unavailable"
        try:
            memory = psutil.virtual_memory()
            metadata.update(ram_total_bytes=memory.total, ram_available_bytes=memory.available,
                            ram_used_bytes=memory.used, ram_percent=memory.percent)
        except (psutil.Error, OSError):
            unavailable["ram"] = "counter_unavailable"
        counters: dict[str, int] = {}
        groups = [("disk", psutil.disk_io_counters,
                   {"read_bytes": "disk_read_bytes_per_sec", "write_bytes": "disk_write_bytes_per_sec"}),
                  ("network", psutil.net_io_counters,
                   {"bytes_sent": "network_sent_bytes_per_sec", "bytes_recv": "network_received_bytes_per_sec"})]
        for group, reader, fields in groups:
            try:
                sample = reader(nowrap=True)
            except (psutil.Error, OSError, RuntimeError):
                sample = None
            for source, target in fields.items():
                metadata[target] = None
                if sample is None:
                    unavailable[target] = "counter_unavailable"
                    continue
                value = getattr(sample, source)
                counters[target] = value
                previous = self._previous_counters.get(target)
                if previous is None:
                    unavailable[target] = "first_sample_warmup"
                elif interval is None or interval <= 0:
                    unavailable[target] = "nonpositive_sample_interval"
                elif value < previous:
                    unavailable[target] = "counter_reset"
                else:
                    metadata[target] = (value - previous) / interval
        metadata["unavailable"] = unavailable
        self._previous_time, self._previous_counters = now, counters
        return [payload(self.name, "system", "SAMPLE", "machine", metadata)]
