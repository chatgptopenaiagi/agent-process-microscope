import json
from pathlib import Path
import unittest
from fixture_support import SyntheticDirectory
from scripts.ci_artifacts import collect

ROOT=Path(__file__).resolve().parents[1]


class InfrastructureTests(unittest.TestCase):
    def test_owned_readonly_file_cleanup_does_not_require_acl_repair(self):
        import stat
        a=SyntheticDirectory();p=Path(a.name)/'synthetic-object'
        p.write_text('SYNTHETIC');p.chmod(stat.S_IREAD)
        a.cleanup()
        self.assertFalse(a.path.exists())

    def test_fixture_is_local_unique_empty_and_cleanup_idempotent(self):
        a,b=SyntheticDirectory(),SyntheticDirectory()
        try:
            self.assertNotEqual(a.name,b.name)
            self.assertTrue(Path(a.name).is_relative_to(ROOT))
            self.assertEqual(list(Path(a.name).iterdir()),[])
            (Path(a.name)/'synthetic.txt').write_text('SYNTHETIC')
            a.cleanup();a.cleanup()
            self.assertTrue(Path(b.name).is_dir())
        finally:a.cleanup();b.cleanup()

    def test_cleanup_requires_ownership_and_scope(self):
        with self.assertRaises(ValueError):SyntheticDirectory(dir=ROOT.parent)
        with self.assertRaises(ValueError):SyntheticDirectory(prefix='../escape')
        a=SyntheticDirectory()
        a.marker.unlink()
        try:
            with self.assertRaises(ValueError):a.cleanup()
            self.assertTrue(a.path.is_dir())
        finally:
            a.marker.write_text('SYNTHETIC ONLY');a.cleanup()

    def test_ci_permissions_actions_and_no_binary_upload(self):
        workflow=json.loads((ROOT/'.github/workflows/windows-qualification.yml').read_text())
        self.assertEqual(workflow['permissions'],{'contents':'read'})
        self.assertNotIn('pull_request_target',workflow['on'])
        for job in workflow['jobs'].values():
            self.assertEqual(job['runs-on'],'windows-2025')
            self.assertLessEqual(job['timeout-minutes'],25)
            for step in job['steps']:
                if 'uses' in step:
                    self.assertRegex(step['uses'],r'^actions/[a-z-]+@[0-9a-f]{40}$')
                    if 'checkout@' in step['uses']:
                        self.assertFalse(step['with']['persist-credentials'])
                        self.assertEqual(step['with']['ref'],'${{ github.event.pull_request.head.sha || github.sha }}')
                    if 'upload-artifact@' in step['uses']:self.assertEqual(step['with']['path'],'cache/ci-public/')
                self.assertNotIn('pull_request.head.',step.get('run',''))
                self.assertNotIn('secrets.',step.get('run',''))

    def test_ci_diagnostics_exclude_databases_and_oversized_logs(self):
        with SyntheticDirectory() as directory:
            root=Path(directory);folder=root/'cache/ci-tests';folder.mkdir(parents=True)
            (folder/'summary.json').write_text('{"status":"SYNTHETIC"}')
            (folder/'private.sqlite3').write_bytes(b'not uploaded')
            (folder/'standard-1.txt').write_bytes(b'x'*(2*1024*1024+1))
            target=collect(root)
            self.assertEqual({p.name for p in target.iterdir()},{'summary.json','standard-1.txt.omitted.txt'})
            with self.assertRaises(FileExistsError):collect(root)

    def test_component_inventory_states_unknown_binary_licenses(self):
        import importlib.metadata as metadata
        from scripts.component_inventory import inventory
        value=inventory(dict(build_dependencies={'psutil':metadata.version('psutil')},
            python='3.14 SYNTHETIC',bundle=[dict(path='_internal/runtime.dll',sha256='0'*64)]))
        self.assertIn('NOT CycloneDX',value['standards_compliance'])
        self.assertEqual(value['legal_clearance'],'PENDING')
        self.assertIn('UNKNOWN',value['binary_inventory'][0]['license'])
        self.assertNotIn(str(ROOT),json.dumps(value))

    def test_component_inventory_rejects_nonportable_binary_paths(self):
        from scripts.component_inventory import inventory
        with self.assertRaises(ValueError):
            inventory(dict(build_dependencies={},python='SYNTHETIC',bundle=[dict(path='../outside.dll',sha256='0'*64)]))
