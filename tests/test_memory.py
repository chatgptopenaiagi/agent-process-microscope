import io
import json
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import struct
import threading
import time
import tkinter as tk
import unittest
from contextlib import closing
from uuid import uuid4

from apm.core.events import Normalizer
from apm.storage.memory import Memory, canonical, explanation
from apm.observatory.client import Outbox
from apm.observatory.codex_stream import CodexStream
from apm.observatory.transport import Receiver, request, receive


class MemoryCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1] / 'cache' / ('memory-tests-' + str(uuid4()))
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root)
        self.path = self.root / 'memory.sqlite3'
        self.memory = Memory(self.path)
        self.addCleanup(self.memory.close)
        self.session, self.stream = str(uuid4()), str(uuid4())
        self.normalizer = Normalizer(self.session, 'controlled-fixture')

    def event(self, **overrides):
        return self.normalizer.normalize(dict(source='fixture', category='command', action='STOP',
                  target='python -m unittest', metadata={'exit_code': 1}) | overrides).to_dict()


class MemoryTests(MemoryCase):
    def test_process_crash_preserves_committed_prefix(self):
        path = self.root / 'crash.sqlite3'
        script = '''import os,sys
from apm.storage.memory import Memory
from apm.core.events import Normalizer
from uuid import uuid4
m=Memory(sys.argv[1])
e=Normalizer(sys.argv[2], 'fixture').normalize(dict(source='fixture',category='test',action='FAIL',status='synthetic',interpretation_level='synthetic'))
m.append(e.to_dict(),str(uuid4()),1)
m.db.execute('BEGIN IMMEDIATE')
m.db.execute('DELETE FROM records')
os._exit(0)
'''
        completed = subprocess.run([sys.executable, '-c', script, str(path), self.session],
            cwd=Path(__file__).resolve().parents[1], timeout=15,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(completed.returncode, 0)
        with Memory(path) as recovered:
            self.assertEqual(recovered.verify()['records'], 1)
            self.assertTrue(recovered.verify()['ok'])

    def test_batch_rollback_is_atomic(self):
        entries = [dict(event=self.event(), stream=self.stream, sequence=1),
                   dict(event=self.event(), stream=self.stream, sequence=1)]
        with self.assertRaises(ValueError):
            self.memory.append_batch(entries)
        self.assertEqual(self.memory.events(self.session), [])
        self.assertTrue(self.memory.verify()['ok'])

    def test_recovery_search_backup_and_integrity(self):
        event = self.event()
        self.memory.append(event, self.stream, 1)
        with Memory(self.path, readonly=True) as reopened:
            self.assertEqual(reopened.events(self.session, search='UNITTEST')[0]['event'], event)
            self.assertEqual(reopened.events(self.session, search="' OR 1=1 --"), [])
            tip = reopened.verify()['tip']
            self.assertTrue(reopened.verify(tip)['ok'])
            reopened.backup(self.root / 'backup.sqlite3')
        with Memory(self.root / 'backup.sqlite3', readonly=True) as backup:
            self.assertTrue(backup.verify(tip)['ok'])
        with self.assertRaises(FileExistsError):
            self.memory.backup(self.root / 'backup.sqlite3')

    def test_duplicate_gap_and_regression_are_explicit(self):
        event = self.event()
        self.memory.append(event, self.stream, 1)
        self.assertTrue(self.memory.append(event, self.stream, 1)['duplicate'])
        with self.assertRaises(ValueError):
            self.memory.append(self.event(), self.stream, 1)
        self.memory.append(self.event(), self.stream, 4)
        self.assertEqual(self.memory.events(self.session)[1]['missing_before'], 2)
        with self.assertRaises(ValueError):
            self.memory.append(self.event(), self.stream, 3)
        self.assertTrue(self.memory.verify()['ok'])

    def test_receipt_order_survives_reversed_source_clocks(self):
        self.memory.append(self.event(timestamp='2030-01-01T00:00:00Z'), self.stream, 1)
        self.memory.append(self.event(timestamp='2020-01-01T00:00:00Z'), str(uuid4()), 1)
        rows = self.memory.events(self.session)
        self.assertGreater(rows[0]['event']['timestamp'], rows[1]['event']['timestamp'])
        self.assertLess(rows[0]['arrival'], rows[1]['arrival'])

    def test_tamper_detection_includes_indexes_and_external_tip(self):
        self.memory.append(self.event(), self.stream, 1)
        tip = self.memory.verify()['tip']
        self.memory.append(self.event(), self.stream, 2)
        self.assertFalse(self.memory.verify(tip)['ok'])
        with self.memory.db:
            self.memory.db.execute('UPDATE records SET session_id=? WHERE arrival=1', (str(uuid4()),))
        self.assertFalse(self.memory.verify()['ok'])

    def test_redaction_precedes_storage_and_classification_is_receiver_owned(self):
        event = self.event(target='tool --password fake-private-value', metadata={'stdout': 'FORBIDDEN-OUTPUT', 'exit_code': 1})
        self.memory.append(event, self.stream, 1, origin='reporter')
        row = self.memory.events(self.session)[0]
        self.assertEqual(row['evidence_class'], 'AGENT_REPORTED')
        text = canonical(row).decode()
        self.assertNotIn('fake-private-value', text)
        self.assertNotIn('FORBIDDEN-OUTPUT', text)
        self.memory.append(self.event(status='synthetic', interpretation_level='synthetic'), str(uuid4()), 1, origin='host')
        self.assertEqual(self.memory.events(self.session)[1]['evidence_class'], 'SYNTHETIC')

    def test_unknown_fields_versions_nonfinite_and_limits_rejected(self):
        for changes in ({'schema_version': '9'}, {'extra': 'private'}, {'confidence': float('nan')}, {'metadata': []}):
            with self.subTest(changes=changes), self.assertRaises((ValueError, TypeError)):
                self.memory.append(self.event() | changes, self.stream, 1)
        with self.assertRaises(ValueError):
            self.memory.events(self.session, limit=101)
        with Memory(self.root / 'small.sqlite3', max_records=1) as small:
            small.append(self.event(), self.stream, 1)
            with self.assertRaises(ValueError):
                small.append(self.event(), self.stream, 2)
            self.assertTrue(small.verify()['ok'])

    def test_unrecognized_database_is_not_migrated(self):
        path = self.root / 'foreign.sqlite3'
        with closing(sqlite3.connect(path)) as db:
            db.execute('CREATE TABLE owner_data(x)')
            db.commit()
        before = path.read_bytes()
        with self.assertRaises(ValueError):
            Memory(path)
        self.assertEqual(path.read_bytes(), before)

    def test_concurrent_writers_and_readers(self):
        errors = []
        def write():
            try:
                with Memory(self.path) as other:
                    stream = str(uuid4())
                    for seq in range(1, 21):
                        other.append(self.event(), stream, seq)
            except Exception as exc:
                errors.append(exc)
        threads = [threading.Thread(target=write) for _ in range(2)]
        for worker in threads:
            worker.start()
        for _ in range(10):
            self.memory.events(self.session)
        for worker in threads:
            worker.join(10)
            self.assertFalse(worker.is_alive())
        self.assertFalse(errors)
        self.assertEqual(self.memory.verify()['records'], 40)
        self.assertTrue(self.memory.verify()['ok'])

    def test_investigation_provenance_and_decisions_never_grant_permission(self):
        event = self.event()
        self.memory.append(event, self.stream, 1)
        result = self.memory.investigate(self.session)
        self.assertEqual(result['findings'][0]['evidence_id'], event['event_id'])
        self.assertIn('root cause may be unavailable', explanation(result))
        self.memory.save_investigation(result)
        self.memory.note(self.session, 'Approved this finding only', decision='approve', references=[event['event_id']])
        rows = self.memory.events(self.session)
        self.assertEqual(rows[1]['evidence_class'], 'INFERRED')
        self.assertEqual(rows[1]['event']['metadata']['checkpoint'], result['checkpoint'])
        self.assertEqual(rows[2]['evidence_class'], 'HUMAN_RECORDED')
        self.assertIn('never execution permission', rows[2]['event']['metadata']['authority'])
        with self.assertRaises(ValueError):
            self.memory.note(str(uuid4()), 'cross session', references=[event['event_id']])

    def test_codex_stream_discards_private_items_and_outputs(self):
        stream = CodexStream()
        raw = [{'type': 'item.completed', 'item': {'id':'item_1', 'type':'reasoning', 'text':'PRIVATE-REASONING'}},
               {'type':'item.completed','item':{'id':'item_2','type':'command_execution',
                'status':'completed','command':'python -m unittest','exit_code':1,'aggregated_output':'PRIVATE-OUTPUT'}}]
        values = list(stream.read(io.BytesIO(b'\n'.join(canonical(r) for r in raw))))
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0]['metadata']['timestamp_basis'], 'client_receipt_time')
        self.assertNotIn('PRIVATE', str(values))
        malformed = list(CodexStream().read(io.BytesIO(b'{"type":"a","type":"b"}\n')))
        self.assertEqual(malformed[0]['status'], 'unavailable')


class TransportTests(MemoryCase):
    def setUp(self):
        super().setUp()
        self.writer, self.reader = 'a'*64, 'b'*64
        self.server = Receiver(self.memory, {self.writer: {'role':'reporter','session_id':self.session},
                                            self.reader: {'role':'reader','session_id':self.session}})
        self.worker = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval':.05})
        self.worker.start()
        self.port = self.server.server_address[1]
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown(); self.worker.join(5); self.server.server_close()

    def test_auth_scope_roles_and_no_process_control(self):
        event = self.event()
        for key, op, params in [('c'*64,'events',{}), (self.reader,'append',dict(event=event,stream=self.stream,sequence=1)),
                                (self.writer,'events',{}), (self.reader,'execute',{'command':'echo unsafe'}),
                                (self.writer,'append',dict(event=event | {'session_id':str(uuid4())},stream=self.stream,sequence=1))]:
            with self.subTest(op=op), self.assertRaises(ValueError):
                request(self.port, key, op, **params)
        request(self.port, self.writer, 'append', event=event, stream=self.stream, sequence=1)
        self.assertEqual(request(self.port, self.reader, 'events')[0]['evidence_class'], 'AGENT_REPORTED')
        self.assertEqual(request(self.port, self.reader, 'investigate')['findings'][0]['evidence_id'], event['event_id'])

    def test_outbox_survives_disconnect_and_ack_loss(self):
        path = self.root / 'outbox.sqlite3'
        outbox = Outbox(path, capacity=1)
        outbox.enqueue(self.event())
        # Simulate receiver commit followed by lost ack: pending row is retained.
        seq, event = outbox.db.execute('SELECT seq,event FROM pending').fetchone()
        request(self.port, self.writer, 'append', event=json.loads(event), stream=outbox.stream, sequence=seq)
        outbox.close()
        resumed = Outbox(path)
        self.addCleanup(resumed.close)
        self.assertEqual(resumed.pending, 1)
        self.assertEqual(resumed.flush(self.port, self.writer), 1)
        self.assertEqual(resumed.pending, 0)
        self.assertEqual(len(self.memory.events(self.session)), 1)

    def test_outbox_overflow_retains_and_delivers_loss_marker(self):
        path = self.root/'overflow.sqlite3'
        outbox = Outbox(path, capacity=1)
        outbox.enqueue(self.event())
        with self.assertRaises(ValueError):
            outbox.enqueue(self.event())
        outbox.close()
        outbox = Outbox(path, capacity=1); self.addCleanup(outbox.close)
        while outbox.pending:
            outbox.flush(self.port, self.writer)
        rows = self.memory.events(self.session)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]['evidence_class'], 'UNAVAILABLE')
        self.assertEqual(rows[1]['event']['metadata']['dropped_events'], 1)

    def test_separate_companion_process_sends_public_schema_fixture(self):
        cap = self.root / 'reporter.key'
        cap.write_text(json.dumps(dict(credential=self.writer, session_id=self.session)), encoding='utf8')
        raw = canonical({'type':'item.completed','item':{'id':'item_1','type':'command_execution',
                         'command':'synthetic protocol fixture','status':'completed','exit_code':1}})+b'\n'
        completed = subprocess.run([sys.executable, '-m', 'apm', 'feed-codex', '--capability', str(cap),
            '--outbox', str(self.root/'cli.sqlite3'), '--port', str(self.port)], input=raw,
            capture_output=True, timeout=15, cwd=Path(__file__).resolve().parents[1],
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        rows = self.memory.events(self.session)
        self.assertEqual(rows[0]['event']['target'], 'synthetic protocol fixture')
        self.assertEqual(rows[0]['evidence_class'], 'AGENT_REPORTED')

    def test_offline_outbox_survives_receiver_restart(self):
        outbox = Outbox(self.root/'offline.sqlite3'); self.addCleanup(outbox.close)
        outbox.enqueue(self.event())
        self.server.shutdown(); self.worker.join(5); self.server.server_close()
        with self.assertRaises(OSError):
            outbox.flush(self.port, self.writer)
        self.assertEqual(outbox.pending, 1)
        self.server = Receiver(self.memory, {self.writer:{'role':'reporter','session_id':self.session}}, self.port)
        self.worker = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval':.05})
        self.worker.start()
        self.assertEqual(outbox.flush(self.port, self.writer), 1)

    def test_frame_cap_and_duplicate_json_rejected(self):
        for raw in [struct.pack('!I', 65537), struct.pack('!I', 17)+b'{"a":1,"a":true}  ']:
            with socket.create_connection(('127.0.0.1', self.port)) as sock:
                sock.sendall(raw)
                self.assertFalse(receive(sock, 4096)['ok'])


class MemoryGuiTests(MemoryCase):
    def test_native_ask_and_note_use_persisted_evidence(self):
        from apm.ui.memory_window import MemoryWindow
        event = self.event()
        self.memory.append(event, self.stream, 1)
        root = tk.Tk(); root.withdraw()
        window = MemoryWindow(root, self.path)
        self.addCleanup(window.close)
        def pump():
            deadline = time.monotonic()+5
            while window.busy and time.monotonic() < deadline:
                root.update(); time.sleep(.02)
            self.assertFalse(window.busy)
        pump()
        window.load_events(reset=True); pump()
        self.assertEqual(len(window.tree.get_children()), 1)
        window.ask(); pump()
        self.assertIn(event['event_id'], window.text.get('1.0','end'))
        window.note_text.set('Please investigate this evidence')
        window.record_note(); pump()
        self.assertEqual(len(self.memory.events(self.session)), 3)
