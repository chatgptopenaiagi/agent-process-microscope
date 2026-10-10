"""Explicit read-only acceptance check; never launches Codex or saves findings.

Prints aggregate results only. Native widgets are withdrawn, not visually accepted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apm.storage.review import QualificationReview
from apm.ui.qualification_window import QualificationWindow


def source_hashes(path):
    return {suffix: hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
            for suffix in ('', '-wal') for p in [Path(str(path) + suffix)]}


def check(path, session, expected_tip=None):
    before = source_hashes(path)
    pages, found, resolved = [], 0, 0
    with QualificationReview(path, expected_tip=expected_tip) as review:
        assert review.available, 'Integrity failed'
        summary = review.summary(session)
        cursor = 0
        while rows := review.page(session, after=cursor):
            pages.append(len(rows))
            for record in rows:
                if record['origin'] == 'local-investigator':
                    found += 1
                    refs = review.citations(session, record['event']['event_id'])
                    assert refs['checkpoint'].startswith('MATCHES'), 'Saved checkpoint mismatch'
                    assert all(r['record'] for r in refs['references']), 'Missing citation'
                    resolved += len(refs['references'])
            cursor = rows[-1]['arrival']
    root = tk.Tk(); root.withdraw()
    window = QualificationWindow(root, path, session=session, expected_tip=expected_tip)
    gui_pages, opened = [], 0
    def settle():
        deadline = time.monotonic() + 65
        while window.busy and time.monotonic() < deadline:
            root.update(); time.sleep(.01)
        assert not window.busy, 'Widget operation timed out'
    try:
        settle()
        assert window.total == summary['counts'].get('records', 0), 'GUI count mismatch'
        while True:
            gui_pages.append(len(window.records))
            for iid, record in list(window.records.items()):
                if record['origin'] == 'local-investigator':
                    window.tree.selection_set(iid); root.update(); settle()
                    assert window.refs, 'No GUI citations'
                    for index, ref in enumerate(window.refs):
                        window.citation.current(index); window.open_citation()
                        assert ref['record']['event']['event_id'] in window.details.get('1.0', 'end')
                        opened += 1
            if str(window.next['state']) == 'disabled':
                break
            window.next.invoke(); settle()
        assert gui_pages == pages, 'GUI pagination mismatch'
    finally:
        window.close(); window.worker.join(3)
    assert not window.worker.is_alive(), 'Review worker still running'
    unchanged = before == source_hashes(path)
    assert unchanged, 'Source DB/WAL changed during review'
    return dict(counts=summary['counts'], classes=summary['classes'], page_sizes=pages,
        saved_investigations_checked=found, citations_resolved=resolved,
        integrity_ok=summary['integrity']['ok'], expected_tip_checked=expected_tip is not None,
        database_and_wal_unchanged=unchanged, native_widget_pages=gui_pages,
        native_widget_citations_opened=opened, worker_stopped=True, visible_inspection=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    parser.add_argument('--session', required=True)
    parser.add_argument('--expected-tip')
    args = parser.parse_args()
    print(json.dumps(check(args.database, args.session, args.expected_tip), indent=2))
