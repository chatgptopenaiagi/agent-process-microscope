"""Synthetic tests of conservative qualification gates, not live Codex evidence."""
import unittest
from scripts.qualify_codex import diagnostic_labels, evidence_checks


class QualificationTests(unittest.TestCase):
    def row(self, category='agent', **metadata):
        return dict(origin='reporter', evidence_class='AGENT_REPORTED',
                    event=dict(event_id='synthetic-test-id', source='codex',
                               target='python -m unittest test_authorized.py',
                               category=category, metadata=metadata))

    def test_lifecycle_failure_is_not_a_command_or_authenticated_workflow(self):
        result = evidence_checks([self.row(codex_event='turn.failed')])
        self.assertEqual(result['command_failure_ids'], [])
        self.assertFalse(result['turn_completed'])
        self.assertEqual(result['process_generation_records'], 0)

    def test_command_completion_requires_nonzero_integer_and_report_provenance(self):
        row = self.row('command', codex_event='item.completed', exit_code=1)
        self.assertEqual(evidence_checks([row])['command_failure_ids'], ['synthetic-test-id'])
        for code in (False, True, 0, '1', None):
            row['event']['metadata']['exit_code'] = code
            self.assertEqual(evidence_checks([row])['command_failure_ids'], [])
        row['event']['metadata']['exit_code'] = 1
        row['evidence_class'] = 'SYNTHETIC'
        self.assertEqual(evidence_checks([row])['command_failure_ids'], [])
        row['evidence_class'] = 'AGENT_REPORTED'
        row['event']['target'] = 'unrelated failing command'
        self.assertEqual(evidence_checks([row])['command_failure_ids'], [])

    def test_generation_requires_independent_host_origin(self):
        row = self.row('process', create_time=123, pid=2, root_pid=1)
        self.assertEqual(evidence_checks([row])['child_generation_records'], 0)
        row.update(origin='host', evidence_class='OBSERVED')
        self.assertEqual(evidence_checks([row])['child_generation_records'], 1)

    def test_diagnostics_emit_only_fixed_labels(self):
        raw = b'Error loading config: Access is denied (os error 5). password=FAKE-SECRET C:/private/path'
        self.assertEqual(diagnostic_labels(raw), {'configuration_load_failed', 'access_denied'})
        self.assertEqual(diagnostic_labels(b'FAKE-SECRET arbitrary private text'), set())
