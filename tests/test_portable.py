"""Synthetic archive adversaries; no imported executable is launched."""
import hashlib
import json
from pathlib import Path
import shutil
import stat
import unittest
from unittest.mock import patch
from uuid import uuid4
import zipfile

from scripts.qualify_portable import inspect_archive, extract_checked, qualify, safe_name

ROOT = Path(__file__).resolve().parents[1]


class PortableTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'cache' / ('portable-fixture-' + str(uuid4()))
        self.root.mkdir(parents=True)
        self.archive = self.root / 'fixture.zip'

    def tearDown(self):
        # Only our unique synthetic directory, always within the project cache.
        assert self.root.resolve().is_relative_to(ROOT / 'cache')
        shutil.rmtree(self.root)

    def fixture(self, extra=()):
        items = [('APM/APM.exe', b'SYNTHETIC NOT EXECUTABLE'), ('APM/APM-cli.exe', b'SYNTHETIC CLI')]
        with zipfile.ZipFile(self.archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name, value in items + list(extra): z.writestr(name, value)
        self.manifest = {'bundle': [dict(path=n[4:], bytes=len(v), sha256=hashlib.sha256(v).hexdigest()) for n, v in items]}
        self.sha = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        return self.archive, self.sha, self.manifest

    def test_checked_extraction_preserves_archive_and_refuses_overwrite(self):
        args = self.fixture(); before = self.archive.read_bytes()
        files = inspect_archive(*args)
        destination = self.root / 'space in path'
        extract_checked(self.archive, files, destination)
        self.assertEqual((destination / 'APM/APM.exe').read_bytes(), b'SYNTHETIC NOT EXECUTABLE')
        with self.assertRaises(FileExistsError): extract_checked(self.archive, files, destination)
        self.assertEqual(self.archive.read_bytes(), before)

    def test_unapproved_execution_is_blocked_with_durable_result(self):
        self.fixture(); manifest = self.root / 'inventory.json'; manifest.write_text(json.dumps(self.manifest))
        with patch('scripts.qualify_portable.subprocess.run', side_effect=AssertionError('Must not execute')):
            result = qualify(self.archive, self.sha, manifest, self.root / 'inspection')
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['clean_machine'], 'UNVERIFIED')
        self.assertTrue((self.root / 'inspection/qualification.txt').is_file())

    def test_paths_reject_traversal_ads_reserved_and_aliases(self):
        for name in ('../outside', '/APM/x', 'APM/../x', 'APM//x', 'APM/x:stream', 'APM\\x',
                     'APM/NUL.txt', 'APM/com1', 'APM/trailing.', 'APM/trailing ', 'APM/x\x00y', 'APM/./x'):
            with self.subTest(name=name), self.assertRaises(ValueError): safe_name(name)

    def test_duplicate_case_collision_and_unlisted_files_rejected(self):
        for name in ('APM/APM.EXE', 'APM/unreviewed.txt', 'APM/../escape'):
            with self.subTest(name=name):
                args = self.fixture([(name, b'unknown')])
                with self.assertRaises(ValueError): inspect_archive(*args)

    def test_secrets_databases_protected_engine_rejected(self):
        for name in ('codex.exe', 'case.sqlite3', 'case.sqlite3-wal', '.env', 'auth.json', '.git/config', 'credentials.json'):
            with self.subTest(name=name):
                args = self.fixture([('APM/' + name, b'SYNTHETIC')])
                with self.assertRaises(ValueError): inspect_archive(*args)

    def test_symlink_entry_rejected(self):
        self.fixture()
        with zipfile.ZipFile(self.archive, 'a') as z:
            entry = zipfile.ZipInfo('APM/link'); entry.create_system = 3
            entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(entry, 'outside')
        with self.assertRaisesRegex(ValueError, 'Special'):
            inspect_archive(self.archive, hashlib.sha256(self.archive.read_bytes()).hexdigest(), self.manifest)

    def test_tampering_and_inventory_mismatch_rejected(self):
        args = self.fixture()
        with self.assertRaisesRegex(ValueError, 'checksum'): inspect_archive(args[0], '0' * 64, args[2])
        self.manifest['bundle'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'content'): inspect_archive(*args)

    def test_expansion_and_entry_budgets_rejected(self):
        args = self.fixture()
        with patch('scripts.qualify_portable.MAX_TOTAL', 1), self.assertRaisesRegex(ValueError, 'expansion'):
            inspect_archive(*args)
        with patch('scripts.qualify_portable.MAX_ENTRIES', 1), self.assertRaisesRegex(ValueError, 'count'):
            inspect_archive(*args)
        args = self.fixture([('APM/bomb', b'0' * 100000)])
        with self.assertRaisesRegex(ValueError, 'ratio'): inspect_archive(*args)

    def test_failure_is_reported_without_executing_or_overwriting_inputs(self):
        self.fixture(); manifest = self.root / 'inventory.json'; manifest.write_text(json.dumps(self.manifest))
        with patch('scripts.qualify_portable.subprocess.run', side_effect=AssertionError('Must not execute')):
            result = qualify(self.archive, '0' * 64, manifest, self.root / 'failed', execute=True)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['subprocesses'], [])
        self.assertTrue((self.root / 'failed/qualification.json').is_file())
