"""Explicit, minimized case reports. No embedded sessions, external assets or execution."""
from html import escape
import json
import os
from pathlib import Path

from apm.core.events import utc_now
from .challenge import challenge, VERSION
from .model import check, ref_key


def case_report(journal, catalog, case_id):
    from apm.evidence.capsule import identifier
    identifier(case_id)
    with journal.snapshot():
        integrity = journal.verify()
        entries = [e for e in journal.all_entries() if e['case_id'] == case_id]
    check(bool(entries), 'case_unknown')
    latest = {e['hypothesis_id']: e for e in entries}
    citations = {}
    for entry in entries:
        for ref in entry['hypothesis']['support'] + entry['hypothesis']['contradict'] + entry['detail'].get('references', []):
            key = ref_key(ref)
            if key in citations:
                continue
            item = dict(reference=ref, status='UNAVAILABLE')
            try:
                r = catalog.resolve(ref)
                item.update(status='RESOLVED', declared_class=r['evidence_class'], source=r['source'],
                    category=r['category'], action=r['action'], event_timestamp=r['event_timestamp'],
                    received_at=r['received_at'], timestamp_basis=r['timestamp_basis'],
                    exit_code=r['attributes'].get('exit_code'), arrival=r['arrival'])
            except ValueError:
                pass
            citations[key] = item
    hashes = {key[0] for key in citations}
    return dict(format='apm-holmes-report', version=1, generated_at=utc_now(),
        software=dict(component='APM Holmes', algorithm=VERSION, journal_schema=1),
        case_id=case_id, title=entries[0]['title'], purpose=entries[0]['purpose'],
        integrity=integrity, evidence_inventory=[c.summary() for c in catalog.selected(hashes)],
        citations=list(citations.values()),
        timeline_summary='Per-capsule receipt indices and declared timestamps are retained in the citation inventory. Cross-source execution order is UNKNOWN.',
        hypotheses=[dict(hypothesis_id=e['hypothesis_id'], revision=e['revision'], state=e['state'],
                         hypothesis=e['hypothesis'], challenge=challenge(e['hypothesis'], catalog)) for e in latest.values()],
        history=entries, conclusion='INSUFFICIENT EVIDENCE to establish a unique cause. Human assessments are retained as interpretations.',
        limitations=['Source and reviewer identities are declarations.', 'Unkeyed checks do not authenticate evidence or prove completeness.',
            'Only cited record metadata is included; original sessions and free-text event targets are excluded.',
            'No legal admissibility, laboratory certification or execution authorization is established.'],
        execution_authority='NONE')


def readable_challenge(value):
    lines = ['Assessment: ' + value['conclusion'].replace('_', ' '), value['conclusion_scope'],
             f"Citations resolved: {len(value['resolved'])}; unavailable: {len(value['unavailable'])}.",
             f"Explicit contrary citations: {len(value['explicit_contradictions'])}; conflicting report groups: {value['conflict_groups']}."]
    lines += value['warnings']
    lines += ['Missing: ' + m['reason'] for m in value['missing']]
    lines += ['Alternative: ' + a for a in value['alternatives']]
    lines += ['Proposed check (not executed): ' + c for c in value['proposed_checks']]
    return '\n\n'.join(lines)


def render_html(report):
    # IDs and links are generated locally, never drawn from imported markup/URLs.
    anchors = {ref_key(item['reference']): f'citation-{n}' for n, item in enumerate(report['citations'])}
    def p(value):
        return '<p>' + escape(str(value)) + '</p>'
    def links(values):
        return ' '.join('<a href="#' + anchors[ref_key(ref)] + '">' + escape(ref['evidence_id']) + '</a>' for ref in values)
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<title>APM investigation report</title><style>body{font:16px system-ui;max-width:1000px;margin:2em auto;padding:1em;line-height:1.5}article{border:1px solid #aaa;padding:1em;margin:1em 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{overflow-wrap:anywhere}</style><body>',
        '<h1>' + escape(report['title']) + '</h1>', p(report['purpose']), p(report['conclusion']),
        '<h2>Checks and limits</h2>', p(report['integrity']['check']), p('Journal tip: ' + report['integrity']['tip']),
        *[p(v) for v in report['limitations']], p(report['timeline_summary']), '<h2>Evidence inventory</h2>']
    for item in report['evidence_inventory']:
        parts.append(p(f"Capsule {item['sha256']}; session {item['session_id']}; {item['records']} retained records. Structure and internal SHA-256 checked; provenance unverified."))
    parts.append('<h2>Competing interpretations</h2>')
    for item in report['hypotheses']:
        value = item['hypothesis']
        parts += ['<article><h3>' + escape(value['claim']) + '</h3>', p('Recorded review state: ' + item['state']),
            p('Uncertainty: ' + value['uncertainty']), p('Supporting references:'), links(value['support']),
            p('Contrary references:'), links(value['contradict']), '<pre>' + escape(readable_challenge(item['challenge'])) + '</pre></article>']
    parts.append('<h2>Complete interpretation history</h2>')
    for entry in report['history']:
        parts += ['<article>', p(f"{entry['created_at']} | {entry['hypothesis_id']} revision {entry['revision']} | {entry['kind']} | {entry['state']}"),
            p('Declared producer: ' + entry['producer'] + ' [' + entry['classification'] + ']'),
            p(entry['hypothesis']['claim']), p(entry['detail'].get('reason', '')),
            '<details><summary>Structured revision</summary><pre>' + escape(json.dumps(entry, indent=2)) + '</pre></details></article>']
    parts.append('<h2>Cited evidence metadata</h2>')
    for item in report['citations']:
        parts += ['<article id="' + anchors[ref_key(item['reference'])] + '"><pre>', escape(json.dumps(item, indent=2)), '</pre></article>']
    parts += [p('Generated: ' + report['generated_at'] + ' | ' + VERSION), '</body></html>']
    return '\n'.join(parts)


def export_report(journal, catalog, case_id, destination):
    destination = Path(destination)
    check(destination.suffix.lower() in ('.json', '.html'), 'report_extension')
    report = case_report(journal, catalog, case_id)
    data = (render_html(report) if destination.suffix.lower() == '.html' else json.dumps(report, ensure_ascii=True, indent=2)).encode('utf-8')
    check(len(data) <= 32 * 1024 * 1024, 'report_size')
    with destination.open('xb') as target:
        target.write(data); target.flush(); os.fsync(target.fileno())
    return dict(bytes=len(data), hypotheses=len(report['hypotheses']), revisions=len(report['history']), citations=len(report['citations']))
