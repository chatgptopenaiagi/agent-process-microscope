"""Fresh-process sanitized Holmes acceptance. Creates only a new reports directory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))


def fixture(directory, count=3):
    from apm.core.events import Normalizer
    from apm.evidence.capsule import export_session
    from apm.storage.memory import Memory
    directory = Path(directory)
    db = directory / 'synthetic.sqlite3'
    case_id, sessions = str(uuid4()), [str(uuid4()), str(uuid4())]
    with Memory(db) as memory:
        for session in sessions:
            normalizer, stream = Normalizer(session, 'synthetic-fixture'), str(uuid4())
            for n in range(count):
                event = normalizer.normalize(dict(source='codex', category='command', action='STOP',
                    status='synthetic', interpretation_level='synthetic', target='synthetic test outcome',
                    metadata=dict(codex_event='item.completed', item_id='fixture-command',
                                  comparison_key='permission-fixture', exit_code=1 if n % 2 == 0 else 0)))
                memory.append(event.to_dict(), stream, n+1)
    paths = []
    for n, session in enumerate(sessions):
        path = directory / f'synthetic-{n}.apmcapsule'
        export_session(db, session, case_id, path); paths.append(path)
    return db, case_id, paths


def proposed(catalog, shas):
    return dict(claim='The agent caused the test failure.', uncertainty='Cause and command-to-process attribution are unknown.',
        support=[catalog.make_ref(shas[0], catalog.page(shas[0])[0]['event_id'])],
        contradict=[catalog.make_ref(shas[1], catalog.page(shas[1])[1]['event_id'])],
        alternatives=['Environmental permissions', 'Source defect', 'Incorrect producer report'],
        missing=[dict(reference=None, reason='Independent environment and command attribution')],
        checks=['Separately authorize a controlled reference run.'])


def worker(directory):
    from apm.holmes.journal import Journal
    from apm.holmes.model import Catalog
    from apm.holmes.report import export_report
    from apm.holmes.cooperation import synthetic_demo
    start = time.perf_counter()
    catalog = Catalog(); shas = [catalog.open(directory / f'synthetic-{n}.apmcapsule') for n in range(2)]
    case_id = str(uuid4()); path = directory / 'investigation.sqlite3'
    with Journal.create(path) as journal:
        h = journal.propose(case_id, 'Synthetic permission investigation', 'Exercise the interpretation workflow.',
            'Synthetic reviewer declaration', proposed(catalog, shas), catalog, request_id=str(uuid4()), producer_class='SYNTHETIC')
        for kind, detail in [('CHALLENGE', {}),
            ('REVIEW', dict(state='SUPPORTED_WITH_LIMITATIONS', reason='Fixture review only; unique cause unestablished.')),
            ('CORRECT', dict(state='INSUFFICIENT_EVIDENCE', reason='Correction: contrary outcome weakens this interpretation.'))]:
            h = journal.revise(h['hypothesis_id'], h['revision'], 'Synthetic reviewer declaration', kind,
                               detail, catalog, request_id=str(uuid4()), producer_class='SYNTHETIC')
        tip = journal.verify()['tip']
    with Journal(path) as journal:
        integrity = journal.verify(tip); history = journal.all_entries()
        assert len(history) == 4 and [e['kind'] for e in history] == ['CREATE', 'CHALLENGE', 'REVIEW', 'CORRECT']
        assert history[-2]['state'] == 'SUPPORTED_WITH_LIMITATIONS' and history[-1]['state'] == 'INSUFFICIENT_EVIDENCE'
        assert all(e['execution_authority'] == 'NONE' for e in history)
        for role in ('support', 'contradict'):
            assert all(catalog.resolve(ref) for ref in h['hypothesis'][role])
        reports = {suffix: export_report(journal, catalog, case_id, directory / ('case.'+suffix)) for suffix in ('html', 'json')}
        backup = journal.backup(directory / 'backup.sqlite3')
        assert backup['tip'] == tip
    result = dict(status='PASSED', fixture='SYNTHETIC', capsules=2, revisions=4, integrity=integrity,
        reports=reports, reopened=True, execution_authority='NONE', seconds=time.perf_counter()-start,
        cooperation=synthetic_demo(catalog))
    (directory / 'worker-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--worker', type=Path)
    args = parser.parse_args()
    if args.worker:
        worker(args.worker); return
    directory = ROOT / 'reports' / ('holmes-acceptance-' + str(uuid4())); directory.mkdir()
    db, _, paths = fixture(directory)
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [db, *paths]}
    completed = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker', str(directory)],
        cwd=ROOT, capture_output=True, text=True, timeout=60, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if completed.returncode:
        raise RuntimeError('Synthetic acceptance child failed: ' + completed.stderr[-1500:])
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [db, *paths]}
    assert before == after
    result = json.loads((directory / 'worker-result.json').read_text())
    # Independently recompute the journal chain with stdlib in the parent process.
    import sqlite3
    connection = sqlite3.connect((directory / 'investigation.sqlite3').as_uri() + '?mode=ro', uri=True)
    previous = '0' * 64
    try:
        for body, prior, tip in connection.execute('SELECT body,previous,fingerprint FROM entries ORDER BY seq'):
            assert prior == previous
            assert hashlib.sha256(b'APM-Holmes-journal-v1\0' + bytes.fromhex(prior) + body).hexdigest() == tip
            previous = tip
    finally: connection.close()
    assert previous == result['integrity']['tip']
    result.update(source_hashes_unchanged=True, source_hashes=before, independent_parent_chain_check=True,
                  visible_gui_acceptance=False, artifacts=str(directory))
    (directory / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
