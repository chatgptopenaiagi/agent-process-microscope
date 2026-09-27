"""Bounded workspace metadata snapshots. No file contents or READ claims."""
from __future__ import annotations

import os
from pathlib import Path
import stat
import time
from typing import Any

from apm.adapters.base import ObserverAdapter, payload


EXCLUDED_COMPONENTS = frozenset({".git", ".venv", "venv", "node_modules", "secrets",
                                 ".secrets", "__pycache__", ".ssh", ".aws", ".azure",
                                 ".codex", ".claude"})


def excluded_relative(path: Path) -> bool:
    parts = [part.casefold() for part in path.parts]
    return any(part in EXCLUDED_COMPONENTS or part == ".env" or part.startswith(".env.")
               or part in {"credentials", "credentials.json", "credentials.xml", "auth.json"}
               or part.endswith((".pem", ".key", ".pfx", ".p12")) for part in parts)


def is_reparse(path: Path, info: os.stat_result | None = None) -> bool:
    info = info if info is not None else path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def safe_workspace(workspace: Path) -> Path:
    """Refuse any reparse ancestor rather than following it out of the selected scope."""
    absolute = Path(os.path.abspath(os.fspath(workspace)))
    if excluded_relative(absolute):
        raise ValueError("workspace is inside an excluded private or dependency directory")
    for part in [*reversed(absolute.parents), absolute]:
        if is_reparse(part):
            raise ValueError("workspace contains a symbolic link or reparse point")
    if not absolute.is_dir():
        raise ValueError("workspace must be an existing directory")
    return absolute


class FileSystemObserver(ObserverAdapter):
    name = "filesystem"

    def __init__(self, workspace: Path, excluded_roots: list[Path] | None = None,
                 *, max_files: int = 5000, max_entries: int = 12000,
                 max_scan_seconds: float = 0.5, max_events: int = 256) -> None:
        if min(max_files, max_entries, max_events) < 1 or max_scan_seconds <= 0:
            raise ValueError("filesystem bounds must be positive")
        self.workspace = safe_workspace(workspace)
        root_info = self.workspace.lstat()
        self._root_identity = (root_info.st_dev, root_info.st_ino)
        self.excluded_roots = [Path(os.path.abspath(os.fspath(path))) for path in (excluded_roots or [])]
        self.max_files, self.max_entries = max_files, max_entries
        self.max_scan_seconds, self.max_events = max_scan_seconds, max_events
        self._baseline: dict[str, tuple[int, int]] | None = None
        self._closed = False

    def _event(self, action: str, target: str, metadata: dict[str, Any],
               status: str = "observed") -> dict[str, Any]:
        canonical = {"MODIFY": "WRITE", "SCAN_INCOMPLETE": "UNKNOWN", "EVENT_OVERFLOW": "UNKNOWN"}.get(action, action)
        return payload(self.name, "filesystem", canonical, target, {
            "workspace": str(self.workspace), "scope": "workspace_metadata_only",
            "file_contents_captured": False, "attribution": "unknown",
            "observation_kind": action,
            "change_limit": "WRITE denotes changed size or modification time, not verified content changes.",
            "attribution_limit": "A workspace change does not identify its author or prove a file was read.",
            **metadata}, status=status)

    def _excluded(self, path: Path, relative: Path) -> bool:
        return excluded_relative(relative) or any(path == root or root in path.parents for root in self.excluded_roots)

    def _snapshot(self) -> tuple[dict[str, tuple[int, int]], list[str], int]:
        snapshot: dict[str, tuple[int, int]] = {}
        reasons: list[str] = []
        visited = 0
        deadline = time.monotonic() + self.max_scan_seconds
        try:
            root_info = self.workspace.lstat()
            if is_reparse(self.workspace, root_info) or (root_info.st_dev, root_info.st_ino) != self._root_identity:
                return {}, ["workspace_identity_changed"], 0
        except OSError:
            return {}, ["workspace_unavailable"], 0
        pending = [self.workspace]
        while pending:
            directory = pending.pop()
            try:
                # Recheck at traversal time: a formerly normal directory may have been replaced.
                if any(is_reparse(part) for part in [directory, *directory.parents]
                       if part == self.workspace or self.workspace in part.parents):
                    reasons.append("directory_became_reparse")
                    continue
                with os.scandir(directory) as entries:
                    for entry in entries:
                        if time.monotonic() >= deadline or visited >= self.max_entries:
                            return snapshot, [*reasons, "scan_time_or_entry_limit"], visited
                        visited += 1
                        path = Path(entry.path)
                        relative = path.relative_to(self.workspace)
                        if self._excluded(path, relative):
                            continue
                        try:
                            info = entry.stat(follow_symlinks=False)
                            if is_reparse(path, info):
                                continue
                            if stat.S_ISDIR(info.st_mode):
                                pending.append(path)
                            elif stat.S_ISREG(info.st_mode):
                                if len(snapshot) >= self.max_files:
                                    return snapshot, [*reasons, "file_limit"], visited
                                snapshot[relative.as_posix()] = (info.st_size, info.st_mtime_ns)
                        except OSError:
                            reasons.append("entry_metadata_unavailable")
            except OSError:
                reasons.append("directory_metadata_unavailable")
        try:
            final_info = self.workspace.lstat()
            if is_reparse(self.workspace, final_info) or (final_info.st_dev, final_info.st_ino) != self._root_identity:
                reasons.append("workspace_identity_changed_during_scan")
        except OSError:
            reasons.append("workspace_unavailable_after_scan")
        return snapshot, sorted(set(reasons)), visited

    def poll(self) -> list[dict[str, Any]]:
        if self._closed:
            return []
        current, reasons, entries = self._snapshot()
        if reasons:
            # Crucially, an incomplete scan never replaces the last complete baseline.
            return [self._event("SCAN_INCOMPLETE", str(self.workspace), {
                "reasons": sorted(set(reasons)), "files_observed": len(current),
                "entries_examined": entries, "baseline_preserved": True,
                "deletions_inferred": False}, "unavailable")]
        if self._baseline is None:
            self._baseline = current
            return [self._event("SNAPSHOT", str(self.workspace), {
                "files_observed": len(current), "entries_examined": entries,
                "complete": True, "excluded_components": sorted(EXCLUDED_COMPONENTS)})]
        previous = self._baseline
        changed: list[tuple[str, str, dict[str, Any]]] = []
        for path, (size, modified) in current.items():
            before = previous.get(path)
            if before is None:
                changed.append(("CREATE", path, {"size_bytes": size, "mtime_ns": modified}))
            elif before != (size, modified):
                changed.append(("MODIFY", path, {"size_bytes": size, "mtime_ns": modified,
                                                 "previous_size_bytes": before[0], "previous_mtime_ns": before[1]}))
        for path in previous.keys() - current.keys():
            changed.append(("DELETE", path, {"previous_size_bytes": previous[path][0],
                                             "previous_mtime_ns": previous[path][1]}))
        self._baseline = current
        events = [self._event(action, path, metadata) for action, path, metadata in sorted(changed)[:self.max_events]]
        if len(changed) > self.max_events:
            events.append(self._event("EVENT_OVERFLOW", str(self.workspace), {
                "changes_observed": len(changed), "changes_emitted": self.max_events,
                "changes_omitted": len(changed) - self.max_events,
                "baseline_advanced": True}, "unavailable"))
        return events
