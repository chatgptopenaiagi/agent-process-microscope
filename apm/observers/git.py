"""Optional, bounded Git status and line-count metadata; never patch content."""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from typing import Any

from apm.adapters.base import ObserverAdapter, payload
from .filesystem import EXCLUDED_COMPONENTS, excluded_relative, safe_workspace


class GitProbeError(RuntimeError):
    pass


class GitObserver(ObserverAdapter):
    name = "git"

    def __init__(self, workspace: Path, *, timeout_seconds: float = 5.0,
                 max_output_bytes: int = 1024 * 1024, max_records: int = 128) -> None:
        if timeout_seconds <= 0 or min(max_output_bytes, max_records) < 1:
            raise ValueError("Git bounds must be positive")
        self.workspace = safe_workspace(workspace)
        info = self.workspace.lstat()
        self._workspace_identity = (info.st_dev, info.st_ino)
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes, self.max_records = max_output_bytes, max_records
        self._git = shutil.which("git")
        self._closed = False
        self._last: dict[str, Any] | None = None
        self.repository: Path | None = None

    def _event(self, action: str, metadata: dict[str, Any],
               status: str = "observed") -> dict[str, Any]:
        canonical = "UNKNOWN" if action in {"SAMPLE_UNAVAILABLE", "EVENT_OVERFLOW"} else action
        return payload(self.name, "git", canonical, str(self.workspace), {
            "workspace": str(self.workspace),
            "repository": str(self.repository) if self.repository else None,
            "scope": "selected_workspace_within_repository", "file_contents_captured": False,
            "attribution": "unknown",
            "observation_kind": action,
            "attribution_limit": "Git metadata does not identify the actor responsible for a change.",
            **metadata}, status=status)

    def _run(self, args: list[str], deadline: float, *, extra_config: list[str] | None = None,
             allow_no_match: bool = False) -> bytes:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise GitProbeError("timeout")
        env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
        env.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1",
                   GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM="1", GIT_PAGER="cat")
        command = [self._git, "--no-optional-locks", "-c", "core.fsmonitor=false",
                   "-c", "core.untrackedCache=false", "-c", "core.hooksPath=" + os.devnull,
                   "-c", "core.longpaths=true", "-c", "status.submoduleSummary=false",
                   "-c", "diff.external=", "-c", "core.attributesFile=" + os.devnull,
                   *(extra_config or []), "-C", str(self.workspace), *args]
        options: dict[str, Any] = {"stdin": subprocess.DEVNULL, "stdout": subprocess.PIPE,
                                   "stderr": subprocess.PIPE, "env": env, "shell": False}
        if os.name == "nt":
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = subprocess.SW_HIDE
            options.update(creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startup)
        try:
            process = subprocess.Popen(command, **options)
        except OSError:
            raise GitProbeError("git_launch_unavailable") from None
        outputs = [bytearray(), bytearray()]
        overflow = threading.Event()

        def read_pipe(index: int, pipe: Any) -> None:
            try:
                while chunk := pipe.read(16384):
                    room = self.max_output_bytes - len(outputs[index])
                    outputs[index].extend(chunk[:max(0, room)])
                    if len(chunk) > room:
                        overflow.set()
                        break
            except OSError:
                pass

        readers = [threading.Thread(target=read_pipe, args=(index, pipe), daemon=True)
                   for index, pipe in enumerate((process.stdout, process.stderr))]
        for reader in readers:
            reader.start()
        reason = None
        try:
            while process.poll() is None:
                if overflow.is_set():
                    reason = "output_limit"
                    break
                if time.monotonic() >= deadline:
                    reason = "timeout"
                    break
                time.sleep(min(0.01, max(0.001, deadline - time.monotonic())))
            if reason:
                # Only this observer's bounded Git helper is terminated, never attached work.
                process.kill()
            process.wait(timeout=1.0)
            for reader in readers:
                reader.join(timeout=0.5)
            if reason or overflow.is_set():
                raise GitProbeError(reason or "output_limit")
            if any(reader.is_alive() for reader in readers):
                raise GitProbeError("helper_output_unavailable")
            if process.returncode != 0 and not (allow_no_match and process.returncode == 1):
                raise GitProbeError("git_exit_" + str(process.returncode))
            return bytes(outputs[0])
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1.0)
            raise GitProbeError("helper_shutdown_timeout") from None
        finally:
            for pipe in (process.stdout, process.stderr):
                pipe.close()

    def _allowed_path(self, raw: bytes) -> str | None:
        text = raw.decode("utf-8", "replace").replace("\\", "/")
        path = Path(text)
        if path.is_absolute() or ".." in path.parts or self.repository is None:
            return None
        full = self.repository / path
        try:
            relative = full.relative_to(self.workspace)
        except ValueError:
            return None
        return None if excluded_relative(relative) else relative.as_posix()

    def _parse_status(self, output: bytes) -> tuple[list[dict[str, str]], int]:
        records = output.split(b"\0")
        result = []
        index = 0
        omitted = 0
        while index < len(records):
            record = records[index]
            index += 1
            if not record:
                continue
            if len(record) < 4 or record[2:3] != b" ":
                raise GitProbeError("status_format_unavailable")
            path = self._allowed_path(record[3:])
            entry = {"path": path, "index_status": chr(record[0]), "worktree_status": chr(record[1])}
            if record[:1] in (b"R", b"C") or record[1:2] in (b"R", b"C"):
                if index >= len(records) or not records[index]:
                    raise GitProbeError("rename_metadata_incomplete")
                original = self._allowed_path(records[index])
                index += 1
                if original is not None:
                    entry["previous_path"] = original
            if path is not None:
                if len(result) < self.max_records:
                    result.append(entry)
                else:
                    omitted += 1
        return result, omitted

    def _parse_numstat(self, output: bytes) -> tuple[list[dict[str, Any]], int]:
        result = []
        omitted = 0
        for record in output.split(b"\0"):
            if not record:
                continue
            fields = record.split(b"\t", 2)
            if len(fields) != 3:
                raise GitProbeError("numstat_format_unavailable")
            path = self._allowed_path(fields[2])
            if path is None:
                continue
            try:
                added, removed = [None if field == b"-" else int(field) for field in fields[:2]]
            except ValueError:
                raise GitProbeError("numstat_count_unavailable") from None
            if any(value is not None and value < 0 for value in (added, removed)):
                raise GitProbeError("numstat_count_unavailable")
            if len(result) < self.max_records:
                result.append({"path": path, "added_lines": added, "removed_lines": removed,
                               "binary": added is None or removed is None})
            else:
                omitted += 1
        return result, omitted

    def poll(self) -> list[dict[str, Any]]:
        if self._closed:
            return []
        if self._git is None:
            return [self._event("SAMPLE_UNAVAILABLE", {"reason": "git_not_installed"}, "unavailable")]
        deadline = time.monotonic() + self.timeout_seconds
        try:
            workspace = safe_workspace(self.workspace)
            info = workspace.lstat()
            if (info.st_dev, info.st_ino) != self._workspace_identity:
                raise GitProbeError("workspace_identity_changed")
            root_output = self._run(["rev-parse", "--show-toplevel"], deadline)
            self.repository = safe_workspace(Path(os.fsdecode(root_output).strip()))
            if self.workspace != self.repository and self.repository not in self.workspace.parents:
                raise GitProbeError("repository_outside_selected_scope")
            # Disable local clean/process filters too: --no-textconv alone does not disable them.
            filter_names = self._run(["config", "--includes", "--name-only", "--get-regexp",
                                      r"^filter\..*\.(clean|process|required)$"],
                                     deadline, allow_no_match=True)
            config: list[str] = []
            for raw in filter_names.splitlines():
                key = raw.decode("utf-8", "strict")
                if not re.fullmatch(r"filter\.[A-Za-z0-9_.-]+\.(?:clean|process|required)", key):
                    raise GitProbeError("unsupported_filter_configuration")
                config.extend(["-c", key + ("=false" if key.endswith(".required") else "=")])
            pathspecs = [".", *(":(exclude,glob)**/" + name + "/**" for name in sorted(EXCLUDED_COMPONENTS)),
                         ":(exclude,glob)**/.env*", ":(exclude,glob)**/credentials*",
                         ":(exclude,glob)**/auth.json", ":(exclude,glob)**/*.pem",
                         ":(exclude,glob)**/*.key", ":(exclude,glob)**/*.pfx", ":(exclude,glob)**/*.p12"]
            status_output = self._run(["status", "--porcelain=v1", "-z", "--untracked-files=normal",
                                       "--ignore-submodules=all", "--", *pathspecs], deadline, extra_config=config)
            diff_args = ["diff", "--numstat", "-z", "--no-ext-diff", "--no-textconv",
                         "--no-renames", "--ignore-submodules=all", "--no-relative"]
            unstaged = self._run([*diff_args, "--", *pathspecs], deadline, extra_config=config)
            staged = self._run([*diff_args, "--cached", "--", *pathspecs], deadline, extra_config=config)
            statuses, status_omitted = self._parse_status(status_output)
            unstaged_stats, unstaged_omitted = self._parse_numstat(unstaged)
            staged_stats, staged_omitted = self._parse_numstat(staged)
            current = {"status_entries": statuses, "unstaged_numstat": unstaged_stats,
                       "staged_numstat": staged_stats,
                       "records_omitted": status_omitted + unstaged_omitted + staged_omitted,
                       "snapshot_limit": "Git commands are separate observations, not an atomic transaction."}
            if current == self._last:
                return []
            action = "SNAPSHOT" if self._last is None else "UPDATE"
            self._last = current
            events = [self._event(action, current)]
            if current["records_omitted"]:
                events.append(self._event("EVENT_OVERFLOW", {"records_omitted": current["records_omitted"]}, "unavailable"))
            return events
        except (GitProbeError, OSError, ValueError, UnicodeError) as error:
            reason = str(error) if isinstance(error, GitProbeError) else "workspace_or_metadata_unavailable"
            return [self._event("SAMPLE_UNAVAILABLE", {"reason": reason, "previous_snapshot_preserved": True}, "unavailable")]
