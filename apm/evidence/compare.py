"""Deterministic, cited comparisons; resemblance is never a causal conclusion."""
from collections import Counter, defaultdict

from .capsule import require


def records(capsule):
    after = 0
    while page := capsule.page(after=after):
        yield from page
        after = page[-1]['arrival']


def reference(capsule, record):
    return dict(capsule_sha256=capsule.sha256, session_id=capsule.manifest['session_id'],
                evidence_id=record['event_id'], declared_class=record['evidence_class'])


def outcomes(capsule):
    groups, items, turns = defaultdict(list), defaultdict(list), Counter()
    for record in records(capsule):
        attrs = record['attributes']
        identity = (record['stream'], record['source'], record['evidence_class'])
        if attrs.get('codex_event') == 'turn.started':
            turns[identity] += 1
        if record['category'] != 'command' or 'exit_code' not in attrs or attrs.get('codex_event') != 'item.completed':
            continue
        # Absent task identity stays unspecified; no command text or fuzzy similarity.
        key = (record['source'], record['evidence_class'], attrs.get('comparison_key', 'UNSPECIFIED'))
        groups[key].append(record)
        if 'item_id' in attrs:
            items[(*identity, turns[identity], attrs['item_id'])].append(record)
    conflicts = []
    for group in items.values():
        if len({r['attributes']['exit_code'] for r in group}) > 1:
            conflicts.append(dict(status='CONTRADICTED', basis='Incompatible final exit codes for the same declared stream, observed turn and item',
                evidence=[reference(capsule, r) for r in group[:20]], evidence_total=len(group),
                limitation='Missing turn boundaries or producer errors can affect this grouping; no winner selected.'))
    return groups, conflicts


def compare(left, right):
    require(left.manifest['session_id'] != right.manifest['session_id'], 'comparison_needs_distinct_sessions')
    left_groups, left_conflicts = outcomes(left)
    right_groups, right_conflicts = outcomes(right)
    shared = sorted(set(left_groups) & set(right_groups))
    findings = []
    for key in shared[:40]:
        a, b = left_groups[key], right_groups[key]
        ac, bc = Counter(r['attributes']['exit_code'] for r in a), Counter(r['attributes']['exit_code'] for r in b)
        repeated_failures = sorted(code for code in ac.keys() & bc.keys() if code != 0)
        findings.append(dict(status='INFERRED', match=dict(source=key[0], declared_class=key[1], comparison_key=key[2]),
            claim='Both sessions retain completed command reports in this explicit comparison group.',
            left_outcomes=dict(ac), right_outcomes=dict(bc), shared_nonzero_exit_codes=repeated_failures,
            different_outcomes=set(ac) != set(bc),
            supporting_evidence=dict(left=[reference(left, r) for r in a[:20]], right=[reference(right, r) for r in b[:20]]),
            evidence_totals=dict(left=len(a), right=len(b)),
            unknowns=['Matching labels/exit codes do not establish the same command, environment or cause.',
                      'Different sessions can legitimately have different outcomes; that alone is not a contradiction.'],
            alternatives=['Independent failures with a common exit code', 'A repeated environmental problem', 'Incorrect producer reports'],
            proposed_check='Human selects and separately authorizes an independent environment/command check for each session; no action executed.',
            causal_assessment='INSUFFICIENT EVIDENCE'))
    conflicts = left_conflicts + right_conflicts
    return dict(algorithm='apm-session-comparison-v1', status='INFERRED',
        left=left.summary(), right=right.summary(), findings=findings,
        matched_groups=len(shared), findings_truncated=len(shared) > 40,
        contradictions=conflicts[:40], contradiction_groups=len(conflicts), contradictions_truncated=len(conflicts) > 40,
        uncertainty=['Exporter provenance is unverified; checksum checks establish internal content integrity only.',
                     'Missing citations, undisclosed human records and unknown clocks limit interpretation.',
                     'No cross-node timestamp ordering, source authentication, causal discovery or learned pattern is established.'],
        conclusion='INSUFFICIENT EVIDENCE for a shared cause; review cited similarities, differences and conflicts.')
