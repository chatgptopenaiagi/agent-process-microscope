"""Explicit, bounded synthetic desktop qualification for source and frozen builds.

Never runs at startup. The caller must select a NEW destination. This automated
withdrawn-window workflow is not human visual acceptance or an install test.
"""
import hashlib
import json
from pathlib import Path
import sys
import time


def run(destination):
    import tkinter as tk
    from apm import __version__
    from apm.holmes.journal import Journal
    from apm.ui.holmes_window import HolmesWindow
    directory = Path(destination).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    root = tk.Tk(); root.withdraw()
    window = HolmesWindow(root, data_root=directory / 'data', producer_class='SYNTHETIC')
    def require(condition, message):
        if not condition: raise RuntimeError(message)
    def wait():
        deadline = time.monotonic() + 20
        while window.busy and time.monotonic() < deadline:
            root.update(); time.sleep(.01)
        root.update()
        require(not window.busy, 'GUI operation timed out')
        require('rejected' not in window.status.get(), 'GUI rejected fixture operation')
    def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        require(not window.data_root.exists(), 'Startup wrote user data')
        window.start_demo(); wait()
        require('SYNTHETIC' in window.banner.get(), 'Demo label missing')
        case_path = window.path
        sources = [case_path.parent / 'synthetic-source.sqlite3', *sorted(case_path.parent.glob('*.apmcapsule'))]
        before = {p.name: digest(p) for p in sources}
        require(len(window.catalog.summaries()) == 2, 'Expected two capsules')
        for n, role in enumerate(('support', 'contradict')):
            window.capsules.current(n); window.select_capsule(); wait()
            window.evidence.selection_set(window.evidence.get_children()[n]); root.update()
            window.attach(role)
        window.claim.insert('1.0', 'A synthetic environmental issue caused the reported failure.')
        window.uncertainty.insert('1.0', 'No real cause, identity or command attribution is established.')
        window.alternatives.insert('1.0', 'A source defect\nA fabricated producer report')
        window.checks.insert('1.0', 'Ask a human to authorize a separately captured reference run.')
        window.propose(); wait()
        for n in range(2):
            window.citation_choice.current(n); window.resolve_citation(); wait()
            require('Resolved' in window.summary.get('1.0', 'end'), 'Citation did not resolve')
        window.challenge(); wait()
        require('INSUFFICIENT EVIDENCE' in window.summary.get('1.0', 'end'), 'Challenge conclusion missing')
        window.reason.insert(0, 'Synthetic assessment for qualification only.')
        window.review_state.set('SUPPORTED_WITH_LIMITATIONS'); window.review(); wait()
        window.reason.delete(0, 'end'); window.reason.insert(0, 'Correction: contrary outcomes leave the cause unknown.')
        window.review_state.set('INSUFFICIENT_EVIDENCE'); window.review(True); wait()
        window.close()
        # A new interpreter/widget tree and a newly opened journal exercise reopening.
        root = tk.Tk(); root.withdraw()
        window = HolmesWindow(root, data_root=directory / 'data', producer_class='SYNTHETIC')
        window.open_journal(case_path); wait()
        require(len(window.entries) == 4 and window.current['kind'] == 'CORRECT', 'Revision history lost')
        for path in sources[1:]: window.open_capsule(path); wait()
        window.export(directory / 'investigation.html'); wait()
        require((directory / 'investigation.html').is_file(), 'Report missing')
        window.export(directory / 'investigation.json'); wait()
        with Journal(case_path) as journal:
            integrity = journal.verify()
            require(all(e['execution_authority'] == 'NONE' for e in journal.all_entries()), 'Unexpected action authority')
        require(before == {p.name: digest(p) for p in sources}, 'Source evidence changed')
        result = dict(status='PASSED', fixture='SYNTHETIC', version=__version__, capsules=2,
            citations_resolved=2, revisions=4, reopened=True, source_hashes_unchanged=True,
            source_sha256=before, integrity=integrity, execution_authority='NONE',
            frozen=bool(getattr(sys, 'frozen', False)), module_location=__file__,
            native_widget_workflow=True, visible_human_acceptance=False,
            seconds=round(time.perf_counter() - started, 3))
        with (directory / 'result.json').open('x', encoding='utf-8') as target:
            json.dump(result, target, indent=2)
        return result
    finally:
        if not window.closed: window.close()
