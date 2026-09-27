"""Scoped observer regressions. Temporary evidence stays under the APM root."""
from __future__ import annotations

from contextlib import nullcontext
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import psutil

from apm.observers.filesystem import FileSystemObserver, safe_workspace
from apm.observers.git import GitObserver, GitProbeError
from apm.observers.process import ProcessObserver
from apm.observers.system import SystemObserver


APM_ROOT = Path(__file__).resolve().parents[1]


class ScopedTemporaryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix=".observer-test-", dir=APM_ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)


class FileSystemObserverTests(ScopedTemporaryTest):
    def test_metadata_changes_are_not_read_claims(self):
        path = self.root / "owned.txt"
        path.write_text("one", encoding="utf-8")
        observer = FileSystemObserver(self.root)
        self.assertEqual(observer.poll()[0]["action"], "SNAPSHOT")
        path.write_text("two words", encoding="utf-8")
        changed = observer.poll()
        self.assertEqual([(item["action"], item["target"]) for item in changed], [("WRITE", "owned.txt")])
        self.assertFalse(changed[0]["metadata"]["file_contents_captured"])
        self.assertNotIn("two words", json.dumps(changed))
        path.unlink()
        self.assertEqual(observer.poll()[0]["action"], "DELETE")
        self.assertNotIn("READ", json.dumps(changed))

    def test_incomplete_scan_never_infers_deletions_or_advances_baseline(self):
        (self.root / "owned.txt").write_text("data", encoding="utf-8")
        observer = FileSystemObserver(self.root)
        observer.poll()
        original = observer._baseline.copy()
        with patch.object(observer, "_snapshot", return_value=({}, ["file_limit"], 1)):
            events = observer.poll()
        self.assertEqual(events[0]["status"], "unavailable")
        self.assertTrue(events[0]["metadata"]["baseline_preserved"])
        self.assertEqual(observer._baseline, original)
        self.assertEqual(observer.poll(), [])

    def test_actual_scan_bounds_and_exclusions(self):
        for directory in [".git", ".venv", "node_modules", "secrets", ".secrets", ".codex"]:
            target = self.root / directory
            target.mkdir()
            (target / "hidden.txt").write_text("not inspected", encoding="utf-8")
        (self.root / ".env").write_text("TOKEN=private", encoding="utf-8")
        (self.root / "credential.key").write_text("private", encoding="utf-8")
        (self.root / "a.txt").write_text("a", encoding="utf-8")
        (self.root / "b.txt").write_text("b", encoding="utf-8")
        observer = FileSystemObserver(self.root, max_files=1)
        self.assertEqual(observer.poll()[0]["metadata"]["observation_kind"], "SCAN_INCOMPLETE")
        self.assertIsNone(observer._baseline)
        (self.root / "b.txt").unlink()
        self.assertEqual(observer.poll()[0]["metadata"]["files_observed"], 1)
        self.assertEqual(set(observer._baseline), {"a.txt"})

    def test_explicit_excluded_session_root_and_overflow(self):
        session = self.root / "sessions"
        session.mkdir()
        (session / "events.jsonl").write_text("not observed", encoding="utf-8")
        observer = FileSystemObserver(self.root, [session], max_events=1)
        self.assertEqual(observer.poll()[0]["metadata"]["files_observed"], 0)
        (self.root / "a").touch()
        (self.root / "b").touch()
        events = observer.poll()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1]["metadata"]["changes_omitted"], 1)
        self.assertEqual(events[1]["status"], "unavailable")

    def test_symlink_is_not_followed_and_cannot_be_workspace(self):
        workspace = self.root / "workspace"
        outside = self.root / "outside"
        workspace.mkdir()
        outside.mkdir()
        (outside / "secret.txt").write_text("not observed", encoding="utf-8")
        link = workspace / "escape"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Creating a test symlink is unavailable")
        observer = FileSystemObserver(workspace)
        self.assertEqual(observer.poll()[0]["metadata"]["files_observed"], 0)
        with self.assertRaises(ValueError):
            safe_workspace(link)
        with self.assertRaises(ValueError):
            safe_workspace(link / "nested")

    def test_replaced_workspace_does_not_generate_deletes(self):
        workspace = self.root / "workspace"
        workspace.mkdir()
        (workspace / "a").touch()
        observer = FileSystemObserver(workspace)
        observer.poll()
        workspace.rename(self.root / "old")
        workspace.mkdir()
        event = observer.poll()[0]
        self.assertEqual(event["status"], "unavailable")
        self.assertIn("workspace_identity_changed", event["metadata"]["reasons"])

    def test_private_history_directory_cannot_be_selected_as_workspace(self):
        history = self.root / ".codex"
        history.mkdir()
        with self.assertRaises(ValueError):
            FileSystemObserver(history)
        with self.assertRaises(ValueError):
            GitObserver(history)

    def test_close_stops_observation(self):
        observer = FileSystemObserver(self.root)
        observer.close()
        self.assertEqual(observer.poll(), [])


class FakeProcess:
    def __init__(self, pid, created, *, name="python.exe", argv=None, children=None):
        self.pid, self.created = pid, created
        self._name = name
        self._argv = argv or [name]
        self._children = children or []
        self.command_reads = 0

    def create_time(self):
        return self.created

    def oneshot(self):
        return nullcontext()

    def name(self):
        return self._name

    def ppid(self):
        return 100

    def status(self):
        return "running"

    def memory_info(self):
        return SimpleNamespace(rss=1024)

    def num_threads(self):
        return 1

    def cpu_percent(self, interval=None):
        return 20.0

    def children(self, recursive=False):
        return self._children

    def cmdline(self):
        self.command_reads += 1
        return self._argv


class ProcessObserverTests(unittest.TestCase):
    def test_only_verified_tree_and_safe_tool_prefix_are_reported(self):
        test_child = FakeProcess(101, 20, argv=["python.exe", "-m", "pytest", "--secret", "PRIVATE"])
        agent_child = FakeProcess(102, 30, name="codex.exe", argv=["codex.exe", "PRIVATE PROMPT"])
        root = FakeProcess(100, 10, argv=["python.exe", "PRIVATE ROOT"], children=[test_child, agent_child])
        table = {100: root, 101: test_child, 102: agent_child}
        with patch("apm.observers.process.psutil.Process", side_effect=table.__getitem__) as factory:
            observer = ProcessObserver(100)
            events = observer.poll()
            observer.close()
            self.assertEqual(observer.poll(), [])
        self.assertEqual({call.args[0] for call in factory.call_args_list}, {100, 101, 102})
        self.assertEqual({event["metadata"]["pid"] for event in events}, {100, 101, 102})
        self.assertEqual(root.command_reads, 0)
        self.assertEqual(agent_child.command_reads, 0)
        commands = [event["metadata"].get("command_line") for event in events]
        self.assertIn(["python", "-m", "pytest"], commands)
        self.assertNotIn("PRIVATE", json.dumps(events))

    def test_pid_reuse_is_not_adopted_and_exit_code_is_unknown(self):
        old = FakeProcess(100, 10)
        current = {100: old}
        with patch("apm.observers.process.psutil.Process", side_effect=current.__getitem__):
            observer = ProcessObserver(100)
            observer.poll()
            current[100] = FakeProcess(100, 999)
            events = observer.poll()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["action"], "STOP")
            self.assertIsNone(events[0]["metadata"]["exit_code"])
            self.assertEqual(events[0]["metadata"]["exit_code_status"], "unknown")
            self.assertEqual(events[0]["metadata"]["reason"], "pid_reused")
            self.assertEqual(observer.poll(), [])

    def test_disappearing_child_does_not_report_parent_exit(self):
        child = FakeProcess(101, 20)
        root = FakeProcess(100, 10, children=[child])
        with patch.object(child, "create_time", side_effect=psutil.NoSuchProcess(101)):
            with patch("apm.observers.process.psutil.Process", return_value=root):
                observer = ProcessObserver(100)
                events = observer.poll()
        self.assertFalse(any(event["action"] == "STOP" for event in events))
        self.assertIn(100, observer._identities)

    def test_access_denied_does_not_fabricate_exit(self):
        root = FakeProcess(100, 10)
        with patch("apm.observers.process.psutil.Process", return_value=root):
            observer = ProcessObserver(100)
            observer.poll()
            with patch.object(root, "memory_info", side_effect=psutil.AccessDenied(100)):
                events = observer.poll()
        self.assertEqual(events[0]["status"], "unavailable")
        self.assertIn(100, observer._identities)

    def test_bound_is_explicit(self):
        root = FakeProcess(100, 10, children=[FakeProcess(101, 20)])
        with patch("apm.observers.process.psutil.Process", return_value=root):
            events = ProcessObserver(100, max_processes=1).poll()
        self.assertEqual(events[-1]["metadata"]["observation_kind"], "SCAN_INCOMPLETE")

    def test_current_owned_process_observation_close_never_terminates(self):
        observer = ProcessObserver(os.getpid(), capture_tool_argv=False)
        events = observer.poll()
        self.assertTrue(any(event["metadata"]["pid"] == os.getpid() for event in events))
        observer.close()
        self.assertTrue(psutil.pid_exists(os.getpid()))


class SystemObserverTests(unittest.TestCase):
    def test_monotonic_rates_warmup_and_counter_reset(self):
        memory = SimpleNamespace(total=1000, available=400, used=600, percent=60.0)
        disks = [SimpleNamespace(read_bytes=100, write_bytes=200),
                 SimpleNamespace(read_bytes=140, write_bytes=220),
                 SimpleNamespace(read_bytes=1, write_bytes=2)]
        network = [SimpleNamespace(bytes_sent=100, bytes_recv=200),
                   SimpleNamespace(bytes_sent=160, bytes_recv=280),
                   SimpleNamespace(bytes_sent=170, bytes_recv=300)]
        with patch("apm.observers.system.time.monotonic", side_effect=[100, 102, 103]), \
             patch("apm.observers.system.psutil.cpu_percent", return_value=25), \
             patch("apm.observers.system.psutil.virtual_memory", return_value=memory), \
             patch("apm.observers.system.psutil.disk_io_counters", side_effect=disks), \
             patch("apm.observers.system.psutil.net_io_counters", side_effect=network):
            observer = SystemObserver()
            first, second, third = [observer.poll()[0]["metadata"] for _ in range(3)]
        self.assertIsNone(first["cpu_percent"])
        self.assertIsNone(first["disk_read_bytes_per_sec"])
        self.assertEqual(second["disk_read_bytes_per_sec"], 20)
        self.assertEqual(second["network_received_bytes_per_sec"], 40)
        self.assertEqual(second["ram_available_bytes"], 400)
        self.assertEqual(second["attribution"], "unknown")
        self.assertIsNone(third["disk_read_bytes_per_sec"])
        self.assertEqual(third["unavailable"]["disk_read_bytes_per_sec"], "counter_reset")

    def test_unavailable_disk_is_not_zero_and_close_is_passive(self):
        with patch("apm.observers.system.psutil.disk_io_counters", return_value=None):
            observer = SystemObserver()
            event = observer.poll()
        self.assertIsNone(event[0]["metadata"]["disk_read_bytes_per_sec"])
        observer.close()
        self.assertEqual(observer.poll(), [])


@unittest.skipUnless(shutil.which("git"), "Git is optional")
class GitObserverTests(ScopedTemporaryTest):
    def git(self, *args):
        options = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "stdin": subprocess.DEVNULL,
                   "timeout": 5, "check": True}
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NO_WINDOW
        return subprocess.run([shutil.which("git"), "-C", str(self.root), *args], **options)

    def setUp(self):
        super().setUp()
        self.git("init", "-q")

    def test_staged_unstaged_metadata_without_content_and_no_repository_writes(self):
        path = self.root / "sample.txt"
        path.write_text("original\n", encoding="utf-8")
        self.git("add", "sample.txt")
        path.write_text("replacement PRIVATE_CONTENT\nmore\n", encoding="utf-8")
        index = self.root / ".git" / "index"
        before = (index.stat().st_size, index.stat().st_mtime_ns, index.read_bytes())
        observer = GitObserver(self.root)
        events = observer.poll()
        self.assertEqual(events[0]["status"], "observed", events)
        metadata = events[0]["metadata"]
        self.assertEqual(metadata["unstaged_numstat"][0]["added_lines"], 2)
        self.assertEqual(metadata["staged_numstat"][0]["added_lines"], 1)
        self.assertNotIn("PRIVATE_CONTENT", json.dumps(events))
        self.assertEqual(observer.poll(), [])
        self.assertEqual(before, (index.stat().st_size, index.stat().st_mtime_ns, index.read_bytes()))
        self.assertFalse((self.root / ".git" / "index.lock").exists())

    def test_subdirectory_scope_and_secret_exclusions(self):
        workspace = self.root / "scope"
        workspace.mkdir()
        (workspace / "inside.txt").write_text("inside\n", encoding="utf-8")
        (self.root / "outside.txt").write_text("outside\n", encoding="utf-8")
        (workspace / "secrets").mkdir()
        (workspace / "secrets" / "hidden.txt").write_text("secret\n", encoding="utf-8")
        self.git("add", ".")
        events = GitObserver(workspace).poll()
        self.assertEqual(events[0]["status"], "observed", events)
        data = events[0]["metadata"]
        self.assertEqual([item["path"] for item in data["status_entries"]], ["inside.txt"])
        self.assertEqual([item["path"] for item in data["staged_numstat"]], ["inside.txt"])
        self.assertNotIn("outside.txt", json.dumps(data))
        self.assertNotIn("hidden.txt", json.dumps(data))

    def test_clean_filters_are_disabled(self):
        (self.root / "sample.txt").write_text("before\n", encoding="utf-8")
        self.git("add", "sample.txt")
        (self.root / "sample.txt").write_text("after\n", encoding="utf-8")
        (self.root / ".gitattributes").write_text("sample.txt filter=observer-test\n", encoding="utf-8")
        # An intentionally invalid required filter would fail the diff if executed.
        self.git("config", "filter.observer-test.clean", "APM_NONEXISTENT_FILTER_COMMAND")
        self.git("config", "filter.observer-test.required", "true")
        events = GitObserver(self.root).poll()
        self.assertEqual(events[0]["status"], "observed", events)
        self.assertTrue(events[0]["metadata"]["unstaged_numstat"])

    def test_included_and_worktree_helper_canaries_are_not_executed(self):
        (self.root / "sample.txt").write_text("before\n", encoding="utf-8")
        self.git("add", "sample.txt")
        (self.root / "sample.txt").write_text("after\n", encoding="utf-8")
        (self.root / ".gitattributes").write_text("sample.txt filter=observer-canary\n", encoding="utf-8")
        included = self.root / ".git" / "included-config"
        # Git for Windows runs filter commands in its bundled sh. Every canary is confined to this temp repo.
        included.write_text('[filter "observer-canary"]\n clean = "echo executed > filter-canary.txt; cat"\n required = true\n', encoding="utf-8")
        self.git("config", "include.path", str(included))
        self.git("config", "extensions.worktreeConfig", "true")
        self.git("config", "--worktree", "filter.observer-canary.process", "echo executed > process-canary.txt")
        self.git("config", "core.fsmonitor", "echo executed > fsmonitor-canary.txt")
        events = GitObserver(self.root).poll()
        self.assertEqual(events[0]["status"], "observed", events)
        self.assertTrue(events[0]["metadata"]["unstaged_numstat"])
        for filename in ["filter-canary.txt", "process-canary.txt", "fsmonitor-canary.txt"]:
            self.assertFalse((self.root / filename).exists(), filename)

    def test_bounded_hidden_helper_timeout_and_output(self):
        observer = GitObserver(self.root, max_output_bytes=1024)
        real_popen = subprocess.Popen
        launched = []

        def launcher(command, **kwargs):
            self.assertFalse(kwargs["shell"])
            self.assertEqual(kwargs["env"]["GIT_OPTIONAL_LOCKS"], "0")
            if os.name == "nt":
                self.assertTrue(kwargs["creationflags"] & subprocess.CREATE_NO_WINDOW)
            process = real_popen([sys.executable, "-c", "import time; time.sleep(5)"], **kwargs)
            launched.append(process)
            return process

        with patch("apm.observers.git.subprocess.Popen", side_effect=launcher):
            with self.assertRaisesRegex(GitProbeError, "timeout"):
                observer._run(["status"], time.monotonic() + 0.1)
        self.assertTrue(all(process.poll() is not None for process in launched))

        def noisy_launcher(command, **kwargs):
            return real_popen([sys.executable, "-c", "import sys; sys.stdout.write('x'*100000)"], **kwargs)

        with patch("apm.observers.git.subprocess.Popen", side_effect=noisy_launcher):
            with self.assertRaisesRegex(GitProbeError, "output_limit"):
                observer._run(["status"], time.monotonic() + 3)

    def test_git_unavailable_is_explicit(self):
        observer = GitObserver(self.root)
        observer._git = None
        event = observer.poll()[0]
        self.assertEqual(event["status"], "unavailable")
        self.assertEqual(event["metadata"]["reason"], "git_not_installed")

    def test_rename_and_binary_metadata_parser(self):
        observer = GitObserver(self.root)
        observer.repository = self.root
        result, omitted = observer._parse_status(b"R  new.txt\0old.txt\0")
        self.assertEqual(result[0]["previous_path"], "old.txt")
        result, omitted = observer._parse_numstat(b"-\t-\timage.bin\0")
        self.assertIsNone(result[0]["added_lines"])
        self.assertTrue(result[0]["binary"])


if __name__ == "__main__":
    unittest.main()
