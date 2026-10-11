import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import unittest
from unittest.mock import patch
from uuid import uuid4
from fixture_support import SyntheticDirectory
from scripts.holmes_demo import fixture, proposed
from apm.holmes.journal import Journal
from apm.holmes.model import Catalog
from apm.holmes.report import export_report


class RecoveryQualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp=SyntheticDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'Unicode café case';self.root.mkdir()
        self.db,self.case,self.capsules=fixture(self.root)
        self.catalog=Catalog();shas=[self.catalog.open(p) for p in self.capsules]
        self.journal=Journal.create(self.root/'journal.sqlite3');self.addCleanup(self.journal.close)
        self.journal.propose(self.case,'Synthetic case','Recovery qualification','Synthetic author',
            proposed(self.catalog,shas),self.catalog,request_id=str(uuid4()),producer_class='SYNTHETIC')
        self.before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [self.db,*self.capsules]}

    def assert_preserved(self):
        self.assertEqual(self.before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.before})

    def test_interrupted_export_never_publishes_incomplete_final_name(self):
        path=self.root/'case.html'
        with patch('apm.holmes.report.os.fsync',side_effect=OSError('Synthetic flush failure')):
            with self.assertRaises(OSError):export_report(self.journal,self.catalog,self.case,path)
        self.assertFalse(path.exists())
        self.assertEqual(len(list(self.root.glob('*.partial'))),1)
        export_report(self.journal,self.catalog,self.case,path)
        self.assertIn('Cited evidence',path.read_text(encoding='utf-8'))
        with self.assertRaises(FileExistsError):export_report(self.journal,self.catalog,self.case,path)
        self.assert_preserved()

    def test_restored_backup_citations_and_readonly_chain_inspection(self):
        backup=self.root/'backup.sqlite3';result=self.journal.backup(backup)
        restored=self.root/'restored.sqlite3';shutil.copyfile(backup,restored)
        with Journal(restored) as journal:
            self.assertEqual(journal.verify()['tip'],result['tip'])
            for entry in journal.all_entries():
                for role in ('support','contradict'):
                    for ref in entry['hypothesis'][role]:self.assertTrue(self.catalog.resolve(ref))
        before=hashlib.sha256(backup.read_bytes()).hexdigest()
        with sqlite3.connect(backup.as_uri()+'?mode=ro',uri=True) as reader:
            self.assertEqual(reader.execute('PRAGMA quick_check').fetchone()[0],'ok')
            with self.assertRaises(sqlite3.OperationalError):reader.execute('CREATE TABLE forbidden(x)')
        reader.close()
        self.assertEqual(before,hashlib.sha256(backup.read_bytes()).hexdigest())
        self.assert_preserved()

    def test_corrupted_copy_is_rejected_without_changing_original(self):
        backup=self.root/'backup.sqlite3';self.journal.backup(backup)
        bad=self.root/'corrupt.sqlite3';bad.write_bytes(b'SYNTHETIC NOT SQLITE')
        with self.assertRaises((ValueError,sqlite3.Error)):Journal(bad)
        self.assertEqual(self.journal.verify()['entries'],1)
        self.assert_preserved()
