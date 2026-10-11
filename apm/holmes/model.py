"""Bounded hypothesis contracts and digest-scoped, read-only evidence access."""
from copy import deepcopy

from apm.evidence.capsule import Capsule, fingerprint, identifier
from apm.evidence.compare import records
from apm.security.redaction import sanitize

STATES = ('PROPOSED', 'UNDER_REVIEW', 'SUPPORTED_WITH_LIMITATIONS', 'CONTRADICTED',
          'INSUFFICIENT_EVIDENCE', 'REJECTED', 'SUPERSEDED')
FIELDS = {'claim', 'support', 'contradict', 'alternatives', 'missing', 'checks', 'uncertainty'}


def check(condition, code):
    if not condition:
        raise ValueError('holmes_' + code)


def text(value, limit=2000):
    check(isinstance(value, str) and 0 < len(value.strip()) <= limit, 'text_bounds')
    check(not any(0xD800 <= ord(c) <= 0xDFFF for c in value), 'invalid_unicode')
    clean = sanitize(value.strip())
    check(bool(clean.strip()), 'empty_sanitized_text')
    return clean


def texts(values):
    check(isinstance(values, list) and len(values) <= 20, 'list_bounds')
    return [text(value) for value in values]


def reference(value):
    check(isinstance(value, dict) and set(value) == {'capsule_sha256', 'session_id', 'evidence_id'}, 'reference_fields')
    fingerprint(value['capsule_sha256'])
    identifier(value['session_id'])
    identifier(value['evidence_id'])
    return dict(value)


def ref_key(ref):
    return (ref['capsule_sha256'], ref['session_id'], ref['evidence_id'])


def refs(values):
    check(isinstance(values, list) and len(values) <= 40, 'reference_limit')
    result = [reference(value) for value in values]
    check(len({ref_key(r) for r in result}) == len(result), 'duplicate_reference')
    return result


def hypothesis(value, catalog=None):
    check(isinstance(value, dict) and set(value) == FIELDS, 'hypothesis_fields')
    result = dict(claim=text(value['claim']), uncertainty=text(value['uncertainty']),
                  support=refs(value['support']), contradict=refs(value['contradict']),
                  alternatives=texts(value['alternatives']), checks=texts(value['checks']))
    check(isinstance(value['missing'], list) and len(value['missing']) <= 20, 'missing_limit')
    result['missing'] = []
    for missing in value['missing']:
        check(isinstance(missing, dict) and set(missing) == {'reference', 'reason'}, 'missing_fields')
        result['missing'].append(dict(reference=reference(missing['reference']) if missing['reference'] is not None else None,
                                      reason=text(missing['reason'])))
    if catalog is not None:
        for ref in result['support'] + result['contradict']:
            catalog.resolve(ref)  # Missing citations belong only in the explicit missing list.
    return result


class Catalog:
    """At most eight explicitly selected capsules (32 MiB input). No source writes."""
    def __init__(self):
        self._capsules = {}

    def add(self, capsule):
        check(isinstance(capsule, Capsule), 'capsule_required')
        check(capsule.sha256 in self._capsules or len(self._capsules) < 8, 'catalog_limit')
        self._capsules[capsule.sha256] = capsule
        return capsule.sha256

    def open(self, path):
        return self.add(Capsule.open(path))

    def resolve(self, ref):
        reference(ref)
        cap = self._capsules.get(ref['capsule_sha256'])
        check(cap is not None, 'capsule_unavailable')
        check(cap.manifest['session_id'] == ref['session_id'], 'session_mismatch')
        record = cap.resolve(ref['evidence_id'])
        check(record is not None, 'citation_missing')
        return record

    def make_ref(self, sha, event_id):
        check(sha in self._capsules, 'capsule_unavailable')
        ref = dict(capsule_sha256=sha, session_id=self._capsules[sha].manifest['session_id'], evidence_id=event_id)
        self.resolve(ref)
        return ref

    def page(self, sha, after=0):
        check(sha in self._capsules, 'capsule_unavailable')
        return self._capsules[sha].page(after=after)

    def summaries(self):
        return [cap.summary() for cap in self._capsules.values()]

    def selected(self, hashes):
        return [self._capsules[h] for h in sorted(set(hashes)) if h in self._capsules]


def inventory(catalog, state):
    hashes = {r['capsule_sha256'] for r in state['support'] + state['contradict']}
    return [deepcopy(c.summary()) for c in catalog.selected(hashes)]
