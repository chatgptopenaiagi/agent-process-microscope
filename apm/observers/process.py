"""Observe an explicitly attached process and its verified descendants only."""
from __future__ import annotations

import time
from collections import deque
from typing import Any

import psutil

from apm.adapters.base import ObserverAdapter, payload


class ProcessObserver(ObserverAdapter):
    name = "process"

    def __init__(self, root_pid: int, *, max_processes: int = 256,
                 max_poll_seconds: float = 0.5, capture_tool_argv: bool = True) -> None:
        if isinstance(root_pid, bool) or not isinstance(root_pid, int) or root_pid <= 0:
            raise ValueError("root_pid must be a positive integer")
        if max_processes < 1 or max_poll_seconds <= 0:
            raise ValueError("process bounds must be positive")
        self.root_pid = root_pid
        self.max_processes = max_processes
        self.max_poll_seconds = max_poll_seconds
        self.capture_tool_argv = capture_tool_argv
        self._closed = False
        self._identities: dict[int, float] = {}
        self._processes: dict[int, psutil.Process] = {}
        self._announced: set[tuple[int, float]] = set()
        self._retired: set[tuple[int, float]] = set()
        self._retired_order: deque[tuple[int, float]] = deque()
        self._attach_pending = True
        self._root_finished = False

    def _event(self, action: str, pid: int, metadata: dict[str, Any],
               status: str = "observed") -> dict[str, Any]:
        canonical = {"ATTACH": "OPEN", "ATTACH_UNAVAILABLE": "UNKNOWN", "EXIT": "STOP",
                     "SAMPLE_UNAVAILABLE": "UNKNOWN", "SCAN_INCOMPLETE": "UNKNOWN"}.get(action, action)
        return payload(self.name, "process", canonical, str(metadata.get("name") or pid), {
            "pid": pid, "root_pid": self.root_pid,
            "scope": "attached_root_and_verified_descendants",
            "observation_kind": action,
            "command_line_captured": bool(metadata.get("command_line")),
            "attribution_limit": "Descendancy is observed; intent and file/network causation are unknown.",
            **metadata}, status=status)

    def _tool_command(self, process: psutil.Process, expected: float, name: str) -> list[str] | None:
        """Recognized descendant tool prefix only, with no arbitrary arguments."""
        if not self.capture_tool_argv or process.pid == self.root_pid:
            return None
        executable = name.casefold().removesuffix(".exe")
        if executable in {"pytest", "py.test", "ctest", "ninja", "cmake", "git", "msbuild"}:
            return [executable]  # The process name already provides the tool identity.
        if executable not in {"python", "python3", "python3.14", "pythonw"}:
            return None
        if psutil.Process(process.pid).create_time() != expected:
            return None
        argv = process.cmdline()
        if psutil.Process(process.pid).create_time() != expected:
            return None
        if len(argv) >= 3 and argv[1] == "-m" and argv[2] in {"pytest", "unittest", "tox", "nox"}:
            return [executable, "-m", argv[2]]
        # Do not expose inline code, scripts, prompts, selectors, or any remaining arguments.
        return None

    def _attach(self) -> list[dict[str, Any]]:
        try:
            process = psutil.Process(self.root_pid)
            created = process.create_time()
        except psutil.NoSuchProcess:
            self._attach_pending = False
            self._root_finished = True
            return [self._event("ATTACH_UNAVAILABLE", self.root_pid,
                                {"reason": "process_not_running", "exit_code": None,
                                 "exit_code_status": "unknown"}, "unavailable")]
        except (psutil.AccessDenied, OSError):
            return [self._event("ATTACH_UNAVAILABLE", self.root_pid,
                                {"reason": "identity_unavailable"}, "unavailable")]
        self._identities[self.root_pid] = created
        self._processes[self.root_pid] = process
        self._attach_pending = False
        return []

    def _retire(self, pid: int, reason: str) -> dict[str, Any]:
        created = self._identities.pop(pid)
        self._processes.pop(pid, None)
        self._announced.discard((pid, created))
        self._retired.add((pid, created))
        self._retired_order.append((pid, created))
        if len(self._retired_order) > self.max_processes * 4:
            self._retired.discard(self._retired_order.popleft())
        if pid == self.root_pid:
            self._root_finished = True
        return self._event("EXIT", pid, {
            "create_time": created, "reason": reason, "exit_code": None,
            "exit_code_status": "unknown",
            "lifecycle_limit": "Exit inferred from missing identity; no process exit code is available."}, "unknown")

    def poll(self) -> list[dict[str, Any]]:
        if self._closed:
            return []
        events: list[dict[str, Any]] = []
        if self._attach_pending:
            events.extend(self._attach())
        deadline = time.monotonic() + self.max_poll_seconds
        queue = list(self._identities)
        seen: set[int] = set()
        bounded = False
        while queue:
            if time.monotonic() >= deadline:
                bounded = True
                break
            pid = queue.pop(0)
            if pid in seen or pid not in self._identities:
                continue
            seen.add(pid)
            process = self._processes[pid]
            expected = self._identities[pid]
            try:
                # Recreate the identity accessor: psutil may cache create_time on an old object.
                if psutil.Process(pid).create_time() != expected:
                    events.append(self._retire(pid, "pid_reused"))
                    continue
                with process.oneshot():
                    info = {"create_time": expected, "name": process.name(),
                            "parent_pid": process.ppid(), "process_status": process.status(),
                            "rss_bytes": process.memory_info().rss,
                            "threads": process.num_threads()}
                tool_command = self._tool_command(process, expected, info["name"])
                if tool_command:
                    info["command_line"] = tool_command
                    info["command_line_limit"] = "Recognized tool prefix only; arguments omitted."
                identity = (pid, expected)
                first = identity not in self._announced
                # Prime psutil's per-process CPU counter. First readings are not a rate.
                cpu = process.cpu_percent(interval=None)
                info["cpu_percent"] = None if first else cpu
                if first:
                    self._announced.add(identity)
                    events.append(self._event("ATTACH" if pid == self.root_pid else "OPEN",
                                              pid, {**info, "lifecycle_limit": "First observation, not an exact start event."}))
                events.append(self._event("SAMPLE", pid, info))
                for child in process.children(recursive=False):
                    if len(self._identities) >= self.max_processes and child.pid not in self._identities:
                        bounded = True
                        continue
                    try:
                        created = child.create_time()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                        # A child disappearing during discovery does not mean its parent exited.
                        continue
                    if (child.pid, created) in self._retired:
                        continue
                    if child.pid not in self._identities:
                        self._identities[child.pid] = created
                        self._processes[child.pid] = child
                    if child.pid not in seen:
                        queue.append(child.pid)
            except psutil.NoSuchProcess:
                if pid in self._identities:
                    events.append(self._retire(pid, "process_identity_no_longer_present"))
            except (psutil.AccessDenied, OSError):
                events.append(self._event("SAMPLE_UNAVAILABLE", pid,
                                          {"create_time": expected, "reason": "access_unavailable"}, "unavailable"))
        if bounded:
            events.append(self._event("SCAN_INCOMPLETE", self.root_pid, {
                "reason": "process_or_time_limit", "max_processes": self.max_processes,
                "tracked_processes": len(self._identities),
                "missed_processes": "unknown"}, "unavailable"))
        return events
