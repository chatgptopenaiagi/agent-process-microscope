"""Provider-neutral offline assessment contract. No provider, transport or execution."""
from uuid import uuid4

from apm.core.events import utc_now
from apm.evidence.capsule import fingerprint, identifier, timestamp
from apm.storage.memory import canonical
from .model import check, hypothesis, ref_key, text

ROLES = ('INVESTIGATOR', 'SKEPTIC', 'EVIDENCE_VERIFIER', 'HUMAN_REVIEWER')
FIELDS = {'protocol', 'message_id', 'role', 'producer', 'model_version', 'created_at', 'scope',
          'hypothesis', 'limits', 'execution_authority'}


def validate(message, catalog):
    check(isinstance(message, dict) and set(message) == FIELDS, 'assessment_fields')
    check(len(canonical(message)) <= 32768, 'assessment_size')
    check(message['protocol'] == 'apm-assessment-v1' and message['role'] in ROLES and
          message['execution_authority'] == 'NONE', 'assessment_contract')
    identifier(message['message_id']); timestamp(message['created_at'])
    producer, model = text(message['producer'], 200), text(message['model_version'], 200)
    scope = message['scope']
    check(isinstance(scope, list) and 1 <= len(scope) <= 8, 'assessment_scope')
    pairs = []
    for item in scope:
        check(isinstance(item, dict) and set(item) == {'capsule_sha256', 'session_id'}, 'scope_fields')
        fingerprint(item['capsule_sha256']); identifier(item['session_id'])
        pairs.append((item['capsule_sha256'], item['session_id']))
    check(len(set(pairs)) == len(pairs), 'duplicate_scope')
    available = {(s['sha256'], s['session_id']) for s in catalog.summaries()}
    check(set(pairs) <= available, 'scope_unavailable')
    value = hypothesis(message['hypothesis'], catalog)
    for ref in value['support'] + value['contradict']:
        check(ref_key(ref)[:2] in pairs, 'citation_outside_scope')
    limits = message['limits']
    check(isinstance(limits, dict) and set(limits) == {'max_response_bytes', 'max_seconds', 'max_tokens'}, 'assessment_limits')
    for key, ceiling in [('max_response_bytes',32768), ('max_seconds',300), ('max_tokens',8192)]:
        check(type(limits[key]) is int and 1 <= limits[key] <= ceiling, 'assessment_budget')
    check(len(canonical(message)) <= limits['max_response_bytes'], 'response_exceeds_budget')
    return dict(message, producer=producer, model_version=model, hypothesis=value)


def verify_batch(messages, catalog):
    check(isinstance(messages, list) and 1 <= len(messages) <= 8, 'assessment_batch')
    validated = [validate(message, catalog) for message in messages]
    check(len({m['message_id'] for m in validated}) == len(validated), 'duplicate_assessment')
    return dict(protocol='apm-assessment-v1', responses=validated,
        check='Response structure, declared scope, bounds and every support/contradiction citation resolved.',
        consensus='NOT_PROOF', producer_identity='UNVERIFIED', conclusion='INSUFFICIENT_EVIDENCE',
        limitations=['Roles are declarations; independence is not established.',
                    'Time/token limits are contract fields; no provider invocation or runtime metering exists.',
                    'Human review and separately authorized actions remain distinct.'], execution_authority='NONE')


def synthetic_demo(catalog):
    summaries = catalog.summaries()
    check(bool(summaries), 'demo_needs_capsule')
    summary = summaries[0]; record = catalog.page(summary['sha256'])[0]
    check(record['evidence_class'] == 'SYNTHETIC', 'demo_needs_synthetic_evidence')
    ref = catalog.make_ref(summary['sha256'], record['event_id'])
    messages = []
    for role, claim in [('INVESTIGATOR', 'Synthetic fixture suggests a reported failure.'),
                        ('SKEPTIC', 'The synthetic outcome does not establish a real cause.')]:
        messages.append(dict(protocol='apm-assessment-v1', message_id=str(uuid4()), role=role,
            producer='Synthetic local fixture', model_version='NO_MODEL', created_at=utc_now(),
            scope=[dict(capsule_sha256=summary['sha256'], session_id=summary['session_id'])],
            hypothesis=dict(claim=claim, support=[ref], contradict=[], alternatives=['Fixture construction'],
                missing=[dict(reference=None, reason='Real-world independent observations')],
                checks=['Human review of fixture scope.'], uncertainty='Synthetic demonstration only.'),
            limits=dict(max_response_bytes=32768, max_seconds=10, max_tokens=2048), execution_authority='NONE'))
    return verify_batch(messages, catalog)
