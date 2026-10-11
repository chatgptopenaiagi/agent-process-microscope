import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4
from scripts.build_provenance import deterministic_zip, digest, verify_lock

ROOT = Path(__file__).resolve().parents[1]


class BuildProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'cache' / ('build-fixture-' + str(uuid4())); self.root.mkdir(parents=True)

    def tearDown(self):
        assert self.root.resolve().is_relative_to(ROOT / 'cache')
        shutil.rmtree(self.root)

    def test_zip_has_stable_order_and_metadata_across_file_mtime_changes(self):
        import os
        bundle = self.root / 'bundle'; bundle.mkdir()
        for name in ('z.txt', 'a.txt'): (bundle / name).write_text('SYNTHETIC ' + name)
        first, second = self.root / 'first.zip', self.root / 'second.zip'
        deterministic_zip(bundle, first, 1791676800)
        os.utime(bundle / 'a.txt', (1800000000, 1800000000))
        deterministic_zip(bundle, second, 1791676800)
        self.assertEqual(digest(first), digest(second))
        with self.assertRaises(FileExistsError): deterministic_zip(bundle, first, 1791676800)

    def test_hash_lock_drift_fails_closed(self):
        lock = self.root / 'lock.json'; lock.write_text(json.dumps({'source': 'SYNTHETIC'}))
        with patch('scripts.build_provenance.installed_inventory', return_value={'source': 'SYNTHETIC'}):
            self.assertEqual(verify_lock('unused', lock), {'source': 'SYNTHETIC'})
        with patch('scripts.build_provenance.installed_inventory', return_value={'source': 'ALTERED'}):
            with self.assertRaisesRegex(ValueError, 'hash lock mismatch'): verify_lock('unused', lock)
