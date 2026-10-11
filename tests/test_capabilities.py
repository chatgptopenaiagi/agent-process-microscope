import copy
import json
from pathlib import Path
import unittest
from scripts.verify_capabilities import verify, validate

ROOT = Path(__file__).resolve().parents[1]


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / 'capabilities/apm-capabilities-v1.json').read_text())
        self.schema = json.loads((ROOT / 'capabilities/apm-capabilities-v1.schema.json').read_text())

    def test_schema_and_repository_references(self):
        self.assertEqual(verify(self.manifest, self.schema)['capabilities'], 12)

    def test_unknown_fields_states_and_missing_permissions_rejected(self):
        for operation in ('extra', 'state', 'permission'):
            m = copy.deepcopy(self.manifest); c = m['capabilities'][0]
            if operation == 'extra': c['autonomous_authority'] = True
            elif operation == 'state': c['verification_status'] = 'CERTIFIED'
            else: del c['permissions']
            with self.subTest(operation=operation), self.assertRaises(ValueError): verify(m, self.schema)

    def test_dangling_nonlocal_duplicate_and_version_rejected(self):
        for operation in ('dangling', 'nonlocal', 'duplicate', 'version'):
            m = copy.deepcopy(self.manifest)
            if operation == 'dangling': m['capabilities'][0]['implementation'] = ['apm/nonexistent.py']
            elif operation == 'nonlocal': m['capabilities'][0]['tests'] = ['../outside.py']
            elif operation == 'duplicate': m['capabilities'].append(m['capabilities'][0])
            else: m['application_version'] = 'unknown'
            with self.subTest(operation=operation), self.assertRaises(ValueError): verify(m, self.schema)

    def test_unsupported_schema_keywords_fail_closed(self):
        schema = dict(self.schema, allOf=[])
        with self.assertRaisesRegex(ValueError, 'Unsupported'): validate(self.manifest, schema)
