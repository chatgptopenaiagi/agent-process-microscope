"""Explicit, minimized case reports. No embedded sessions, external assets or execution."""
from html import escape
import json
import os
from pathlib import Path
from uuid import uuid4

from apm.core.events import utc_now
from apm import __version__
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
        software=dict(component='APM Holmes', algorithm=VERSION, journal_schema=1, application_version=__version__),
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
        return ' '.join('<a href="#' + anchors[ref_key(ref)] + '">Evidence ' + str(int(anchors[ref_key(ref)].split('-')[1]) + 1) + '</a>' for ref in values) or p('None attached; this is a gap, not proof of absence.')
    def details(label, value):
        return '<details><summary>' + escape(label) + '</summary><pre>' + escape(json.dumps(value, indent=2)) + '</pre></details>'
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<title>APM investigation report</title><style>body{font:17px system-ui;color:#172b42;background:#fff;max-width:1000px;margin:2em auto;padding:1em;line-height:1.6}h1{font-size:2.2em;line-height:1.2}h2{margin-top:1.8em}article{border:1px solid #b4c2d1;border-left:5px solid #476b91;border-radius:6px;padding:1em 1.4em;margin:1em 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.85em}a{overflow-wrap:anywhere;color:#164e85;margin-right:1em}summary{cursor:pointer;font-weight:600;padding:.5em 0}:focus-visible{outline:3px solid #155f9a;outline-offset:3px}@media print{body{font-size:11pt}article{break-inside:avoid}}</style><body>',
        '<h1>' + escape(report['title']) + '</h1>', p(report['purpose']),
        '<article><h2>Investigation at a glance</h2>',
        p(f"{len(report['hypotheses'])} explanations, {len(report['citations'])} cited records, {len(report['history'])} preserved revisions."),
        p(report['conclusion']), '</article>',
        '<h2>What happened?</h2>', p('The selected records and interpretations below reconstruct what was retained. Reported outcomes remain producer claims; they are not independent proof of the underlying action.'),
        p(report['timeline_summary']),
        '<h2>How do we know?</h2>', p(report['integrity']['check']),
        details('Journal integrity details and recorded chain tip', report['integrity']),
        *[p(v) for v in report['limitations']], '<h3>Evidence inventory</h3>']
    for n, item in enumerate(report['evidence_inventory'], 1):
        parts.append(p(f"Package {n}: {item['records']} retained records. Structure and internal SHA-256 checked; provenance unverified."))
        parts.append(details(f'Package {n} identifiers and disclosure details', item))
    parts += ['<h2>What remains unknown?</h2>', p('Producer identity, collection completeness and cross-source causal attribution are not established by these integrity checks.')]
    for item in report['hypotheses']:
        parts.append(p(item['hypothesis']['uncertainty']))
        parts += [p('Missing evidence: ' + value['reason']) for value in item['hypothesis']['missing']]
    parts.append('<h2>What does the evidence suggest?</h2>')
    for item in report['hypotheses']:
        value = item['hypothesis']
        parts += ['<article><h3>' + escape(value['claim']) + '</h3>', p('Recorded review state: ' + item['state']),
            p('Uncertainty: ' + value['uncertainty']), p('Supporting references:'), links(value['support']),
            p('Contrary references:'), links(value['contradict']), '<pre>' + escape(readable_challenge(item['challenge'])) + '</pre></article>']
    parts.append('<h2>What should the human investigate next?</h2>')
    checks = list(dict.fromkeys(check for item in report['hypotheses'] for check in item['hypothesis']['checks']))
    parts += [p('Proposed, not executed: ' + check) for check in checks] or [p('No follow-up check has been proposed. Decide which missing observation would most help distinguish the explanations.')]
    parts.append(p('A proposed check or saved human assessment grants no tool execution authority.'))
    parts.append('<h2>Complete interpretation history</h2>')
    for entry in report['history']:
        parts += ['<article>', p(f"{entry['created_at']} | {entry['hypothesis_id']} revision {entry['revision']} | {entry['kind']} | {entry['state']}"),
            p('Declared producer: ' + entry['producer'] + ' [' + entry['classification'] + ']'),
            p(entry['hypothesis']['claim']), p(entry['detail'].get('reason', '')),
            '<details><summary>Structured revision</summary><pre>' + escape(json.dumps(entry, indent=2)) + '</pre></details></article>']
    parts.append('<h2>Cited evidence metadata</h2>')
    for item in report['citations']:
        number = int(anchors[ref_key(item['reference'])].split('-')[1]) + 1
        parts += ['<article id="' + anchors[ref_key(item['reference'])] + '"><h3>Evidence ' + str(number) + '</h3>',
                  p('Citation status: ' + item['status'])]
        if item['status'] == 'RESOLVED':
            parts += [p(f"{item['source']} declares {item['category']} / {item['action']} [{item['declared_class']}]."),
                      p('Reported exit code: ' + str(item['exit_code']) if item['exit_code'] is not None else 'Exit code: UNKNOWN'),
                      p(f"Receipt position: {item['arrival']}. Timestamp basis: {item['timestamp_basis']}. This does not establish execution order.")]
        else:
            parts.append(p('The required evidence package is unavailable in this review. No record contents are inferred.'))
        parts += [details('Full scoped reference and retained metadata', item), '</article>']
    parts += [p('Generated: ' + report['generated_at'] + ' | APM ' + __version__ + ' | ' + VERSION), '</body></html>']
    return '\n'.join(parts)


def export_report(journal, catalog, case_id, destination):
    destination = Path(destination)
    check(destination.suffix.lower() in ('.json', '.html'), 'report_extension')
    report = case_report(journal, catalog, case_id)
    data = (render_html(report) if destination.suffix.lower() == '.html' else json.dumps(report, ensure_ascii=True, indent=2)).encode('utf-8')
    check(len(data) <= 32 * 1024 * 1024, 'report_size')
    if os.path.lexists(destination):
        raise FileExistsError('report_destination_exists')
    partial = destination.with_name('.apm-report-' + str(uuid4()) + '.partial')
    with partial.open('xb') as target:
        target.write(data); target.flush(); os.fsync(target.fileno())
    # Publish only after a complete flushed write. Neither branch overwrites an
    # existing destination. Interrupted partials remain available for inspection.
    if os.name == 'nt':
        os.rename(partial, destination)
    else:
        os.link(partial, destination)
        partial.unlink()
    return dict(bytes=len(data), hypotheses=len(report['hypotheses']), revisions=len(report['history']), citations=len(report['citations']))
