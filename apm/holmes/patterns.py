"""Versioned human-reviewed resemblance rules. Never learned causes or probabilities."""
from collections import Counter

from apm.evidence.capsule import CLASSES, SOURCES, identifier
from apm.evidence.compare import records
from apm.core.events import CATEGORIES, ACTIONS
from .model import check, text

KEYS = {'source', 'category', 'action', 'evidence_class', 'comparison_key', 'exit_code'}


def criteria(value):
    check(isinstance(value, dict) and set(value) <= KEYS, 'pattern_criteria')
    for key, item in value.items():
        if key == 'exit_code': check(type(item) is int and -(2**31) <= item < 2**32, 'pattern_exit')
        else:
            check(text(item, 80) == item, 'pattern_text')
            choices = dict(source=SOURCES, category=CATEGORIES, action=ACTIONS, evidence_class=CLASSES)
            if key in choices: check(item in choices[key], 'pattern_vocabulary')
    return dict(value)


def definition(value):
    check(isinstance(value, dict) and set(value) == {'pattern_id', 'version', 'source_review_revision',
        'description', 'required', 'optional', 'counterexamples', 'review_note', 'disposition'}, 'pattern_fields')
    identifier(value['pattern_id'])
    for name in ('version', 'source_review_revision'):
        check(type(value[name]) is int and value[name] >= 1, 'pattern_revision')
    required, optional = criteria(value['required']), criteria(value['optional'])
    check({'source', 'category', 'evidence_class'} <= set(required) and len(required) >= 4, 'pattern_too_broad')
    check(not (set(required) & set(optional)), 'pattern_duplicate_criteria')
    check(isinstance(value['counterexamples'], list) and len(value['counterexamples']) <= 10, 'pattern_counterexamples')
    counters = [criteria(v) for v in value['counterexamples']]
    check(all(counters), 'empty_counterexample')
    check(value['disposition'] in ('ACTIVE', 'RETIRED'), 'pattern_disposition')
    return dict(value, description=text(value['description']), review_note=text(value['review_note']),
                required=required, optional=optional, counterexamples=counters)


def attributes(record):
    return {key: record.get(key) if key in ('source', 'category', 'action', 'evidence_class')
            else record['attributes'].get(key) for key in KEYS}


def matches(rule, record):
    observed = attributes(record)
    return all(observed[key] == wanted for key, wanted in rule.items())


def needs_reassessment(entries, hypothesis_id, revision):
    return any(e['hypothesis_id'] == hypothesis_id and e['revision'] > revision and
               (e['kind'] == 'REVISE' or e['kind'] in ('REVIEW', 'CORRECT') and e['state'] != 'SUPPORTED_WITH_LIMITATIONS')
               for e in entries)


def retrieve(journal, catalog):
    latest = {}
    with journal.snapshot():
        integrity = journal.verify()
        entries = journal.all_entries()
    for entry in entries:
        if entry['kind'] == 'PATTERN': latest[entry['detail']['pattern_id']] = entry
    check(len(latest) <= 100, 'pattern_limit')
    results = []
    for entry in latest.values():
        pattern = entry['detail']
        if pattern['disposition'] != 'ACTIVE': continue
        source_review = next(e for e in entries if e['hypothesis_id'] == entry['hypothesis_id'] and
                             e['revision'] == pattern['source_review_revision'])
        synthetic_review = 'SYNTHETIC' in (entry['producer_class'], source_review['producer_class'])
        suspended = needs_reassessment(entries, entry['hypothesis_id'], pattern['source_review_revision'])
        found, differences, excluded, total = [], Counter(), 0, 0
        for cap in ([] if suspended else catalog.selected([s['sha256'] for s in catalog.summaries()])):
            for record in records(cap):
                if not matches(pattern['required'], record): continue
                if any(matches(rule, record) for rule in pattern['counterexamples']):
                    excluded += 1; continue
                total += 1
                observed = attributes(record)
                different = {key: dict(expected=value, available=observed[key]) for key, value in pattern['optional'].items() if observed[key] != value}
                differences.update(different.keys())
                if len(found) < 20:
                    found.append(dict(reference=catalog.make_ref(cap.sha256, record['event_id']),
                        matched_required=pattern['required'], optional_differences=different))
        results.append(dict(pattern_id=pattern['pattern_id'], version=pattern['version'],
            description=pattern['description'], source_case=entry['case_id'],
            source_hypothesis=entry['hypothesis_id'], source_review_revision=pattern['source_review_revision'],
            source_review_class=source_review['producer_class'],
            review_status=('REASSESSMENT_REQUIRED' if suspended else 'SYNTHETIC_REVIEW_FIXTURE' if synthetic_review
                           else 'HUMAN_REVIEWED_DECLARATION'), matched_records=total, counterexamples_excluded=excluded,
            citations=found, citations_truncated=total > 20, optional_difference_counts=dict(differences),
            conclusion=('Historical review was revised or withdrawn; pattern matching is suspended.' if suspended else
                        'Resembles the declared reviewed pattern; the current cause is not established.' if total else
                        'No match under the explicit required conditions.'),
            execution_authority='NONE'))
    return dict(algorithm='apm-holmes-pattern-v1', status='INFERRED', patterns=results,
                journal_integrity=integrity,
                limitations=['Exact metadata matching only, not calibrated prediction.',
                             'Missing required attributes do not match; optional differences remain explicit.',
                             'Human review is declared, not authenticated. Similarity never proves a shared cause.'])
