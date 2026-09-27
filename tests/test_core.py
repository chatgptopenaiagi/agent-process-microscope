import json
from pathlib import Path
from queue import Queue
import tempfile
import unittest
from uuid import uuid4

from apm.core.bus import EventBus
from apm.core.events import Event, Normalizer
from apm.core.state import StateEngine, test_runner
from apm.security.redaction import sanitize, redact_text
from apm.storage.reader import read_session
from apm.storage.recorder import Recorder


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.session = str(uuid4())
        self.normalizer = Normalizer(self.session, 'test-agent')

    def event(self, **kwargs):
        return self.normalizer.normalize(dict(source='test', category='process', action='START', **kwargs))

    def test_redaction_of_obvious_secrets_before_storage(self):
        secrets = ['secret-value', 'different-value', 'space secret', 'sk-proj-abcdefghijklmnopqrstuvwxyz', 'jwt-part']
        data = {'command': 'run --password "space secret" OPENAI_API_KEY=secret-value https://x/?token=different-value Authorization: Bearer jwt-part sk-proj-abcdefghijklmnopqrstuvwxyz',
                'nested': {'api_key': 'secret-value'}, 'cmdline': ['cli', '--token', 'different-value'],
                'reasoning': 'never persist this', 'environment': {'PASSWORD': 'secret-value'}}
        serialized = json.dumps(self.event(metadata=data).to_dict())
        for secret in secrets + ['never persist this']:
            self.assertNotIn(secret, serialized)
        self.assertIn('[REDACTED]', serialized)
        self.assertEqual(sanitize({'authorization': 'value'})['authorization'], '[REDACTED]')

    def test_private_key_cookie_and_userinfo(self):
        for sample, secret in [('Cookie: session=abc; other=def', 'abc'),
                               ('https://user:pw@example.test', 'pw'),
                               ('-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----', 'secret')]:
            self.assertNotIn(secret, redact_text(sample))

    def test_schema_and_confidence_reject_invalid(self):
        with self.assertRaises(ValueError): self.event(confidence=float('nan'))
        with self.assertRaises(ValueError): self.event(status='inferred')
        with self.assertRaises(ValueError): self.event(schema_version='9.0')
        e = self.event(metadata={'pid': 12})
        self.assertEqual(Event.from_dict(e.to_dict()), e)
        self.assertTrue(e.raw_reference.startswith('sha256:'))

    def test_bounded_bus_records_drops_and_fans_out(self):
        bus = EventBus(2)
        a, b = [], []
        bus.subscribe(a.append)
        bus.subscribe(b.append)
        for _ in range(3): bus.publish(self.event())
        self.assertEqual(bus.dropped_count, 1)
        self.assertEqual(bus.dispatch(), 2)
        self.assertEqual(a, b)

    def test_derived_states_reference_evidence_and_no_file_attribution(self):
        engine = StateEngine()
        e = self.event(target='python.exe', metadata={'pid': 2, 'cmdline': ['python', '-m', 'pytest']})
        state = engine.accept(e)
        self.assertEqual(state.state, 'TESTING')
        self.assertEqual(state.event_ids, (e.event_id,))
        f = self.normalizer.normalize(dict(source='filesystem', category='file', action='WRITE', target='a.py'))
        state = engine.accept(f)
        self.assertEqual(state.state, 'OBSERVING')
        self.assertIn('actor unverified', state.summary)
        end = self.normalizer.normalize(dict(source='process', category='process', action='STOP', target='python.exe', status='unknown', metadata={'pid': 2, 'exit_code': None}))
        self.assertNotIn('pass', engine.accept(end).summary.lower())

    def test_test_detection_requires_a_direct_runner_not_incidental_text(self):
        for command, expected in [('python -m pytest tests/', 'pytest'), ('ctest --output-on-failure', 'ctest'),
                                  ('npm run test', 'npm test'), ('cargo test', 'cargo test'),
                                  ('dotnet test', 'dotnet test'), ('python -m unittest', 'unittest')]:
            self.assertEqual(test_runner({'command': command}), expected)
        for command in ['echo pytest', 'python -c "print(\'pytest\')"', 'cat pytest.log']:
            self.assertIsNone(test_runner({'command': command}))

    def test_session_roundtrip_and_interrupted_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'session'
            recorder = Recorder(path, {'schema_version': '1.0', 'session_id': self.session, 'status': 'recording'})
            event = self.event(metadata={'token': 'must-not-persist'})
            recorder.record(event)
            recorder.record_state(StateEngine().accept(event))
            recorder.close({'status': 'stopped'})
            info, events, warnings = read_session(path)
            self.assertEqual(events, [event])
            self.assertFalse(warnings)
            with (path / 'events.jsonl').open('ab') as stream: stream.write(b'{"truncated":')
            _, events, warnings = read_session(path)
            self.assertEqual(events, [event])
            self.assertIn('Truncated', warnings[0])
            self.assertNotIn('must-not-persist', (path / 'events.jsonl').read_text())

    def test_midstream_corruption_is_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'session'
            recorder = Recorder(path, {'schema_version': '1.0', 'session_id': self.session})
            recorder.record(self.event())
            recorder.close({'status': 'stopped'})
            with (path / 'events.jsonl').open('a') as f: f.write('{bad json}\n')
            with self.assertRaises(ValueError): read_session(path)


if __name__ == '__main__': unittest.main()
