"""Deterministic checks, not causal discovery or command execution."""
from collections import Counter
import re

from apm.evidence.compare import outcomes
from .model import hypothesis, ref_key

VERSION = 'apm-holmes-challenge-v1'


def challenge(state, catalog):
    state = hypothesis(state)
    resolved, unavailable, classes = [], [], Counter()
    for role in ('support', 'contradict'):
        for ref in state[role]:
            try:
                record = catalog.resolve(ref)
            except ValueError:
                unavailable.append(dict(role=role, reference=ref, status='UNAVAILABLE'))
                continue
            classes[record['evidence_class']] += 1
            resolved.append(dict(role=role, reference=ref, declared_class=record['evidence_class']))
    overlap = sorted(set(map(ref_key, state['support'])) & set(map(ref_key, state['contradict'])))
    capsules = catalog.selected([r['capsule_sha256'] for r in state['support'] + state['contradict']])
    selected = {ref_key(r) for r in state['support'] + state['contradict']}
    scope, conflicts = [], []
    for cap in capsules:
        _, found = outcomes(cap)
        conflicts.extend(found)
        count = sum(k[0] == cap.sha256 for k in selected)
        scope.append(dict(capsule_sha256=cap.sha256, session_id=cap.manifest['session_id'],
            retained=cap.manifest['record_count'], cited=count,
            uncited=cap.manifest['record_count'] - count,
            omitted=cap.manifest['disclosure']['omitted_records'],
            missing_references=cap.manifest['missing_references']))
    warnings = [
        'Checksums check content consistency; producer and human identities are declarations, not authenticated identities.',
        'Source times and clock uncertainty are unknown. Receipt order, adjacency and ancestry do not establish causation.',
        'A resolved citation does not establish that it supports the wording of a claim.',
        'Uncited records may matter; relevance is not inferred from their omission. Collection completeness remains unknown.']
    if classes['SYNTHETIC']:
        warnings.append('Synthetic records test the workflow; they do not demonstrate a real incident.')
    if classes['AGENT_REPORTED']:
        warnings.append('Agent-reported claims require independent corroboration.')
    causal = bool(re.search(r'\b(caus\w*|because|responsible|led to|resulted in)\b', state['claim'], re.I))
    if causal:
        warnings.append('Causal wording detected by a lexical rule; no unique cause or command-to-process attribution is established.')
    if overlap:
        warnings.append('The same reference is marked both supporting and contradicting; explain or correct the interpretation.')
    if not state['alternatives']:
        warnings.append('No alternative explanation was supplied; review alternatives before accepting this interpretation.')
    return dict(algorithm=VERSION, status='INFERRED', conclusion='INSUFFICIENT_EVIDENCE',
        conclusion_scope='This rule-based check does not establish the hypothesis as true or a unique cause.',
        resolved=resolved, unavailable=unavailable, declared_classes=dict(classes), scope=scope,
        explicit_contradictions=state['contradict'], contradictory_roles=len(overlap),
        reported_conflicts=conflicts[:40], conflict_groups=len(conflicts), conflicts_truncated=len(conflicts) > 40,
        missing=state['missing'], alternatives=state['alternatives'], warnings=warnings,
        proposed_checks=state['checks'] or ['Review cited records and separately authorize an independent discriminating check.'],
        execution_authority='NONE')
