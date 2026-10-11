from copy import deepcopy
import unittest
from scripts.release_gates import validate,REQUIRED,REQUIRED_V2


class ReleaseGateTests(unittest.TestCase):
    def test_v2_requires_distinct_owner_and_ci_evidence(self):
        report=self.fixture()
        report['schema_version']=2
        report['gates']=[dict(id=k,description=k,evidence=['synthetic-check'],status='PASS',
                             actor='Synthetic fixture',follow_up='None') for k in sorted(REQUIRED_V2)]
        for gate in report['gates']:
            if gate['id'] in ('OWNER_WINDOWS_TESTS','GITHUB_WINDOWS_CI'):
                gate['status']='PENDING';gate['evidence']=[]
        result=validate(report)
        self.assertFalse(result['release_ready'])
        self.assertEqual(set(result['unresolved']),{'OWNER_WINDOWS_TESTS','GITHUB_WINDOWS_CI'})

    def fixture(self):
        return dict(schema_version=1,version='0.2.0.dev1',gates=[dict(id=k,description=k,evidence=['synthetic-check'],status='PASS',actor='Synthetic fixture',follow_up='None for fixture') for k in sorted(REQUIRED)])

    def test_pending_and_not_applicable_never_imply_release_ready(self):
        for status in ('FAIL','BLOCKED','PENDING','NOT_APPLICABLE'):
            report=self.fixture();report['gates'][0]['status']=status
            self.assertFalse(validate(report)['release_ready'])

    def test_pass_requires_evidence_and_complete_unique_inventory(self):
        report=self.fixture();self.assertTrue(validate(report)['release_ready'])
        report['gates'][0]['evidence']=[]
        with self.assertRaises(ValueError):validate(report)
        report=self.fixture();report['gates'][0]=deepcopy(report['gates'][1])
        with self.assertRaises(ValueError):validate(report)
        report=self.fixture();report['gates'].pop()
        with self.assertRaises(ValueError):validate(report)
