"""Reproducible offline synthetic capsule/comparison/widget qualification.

Creates a NEW ignored report directory. Never opens owner evidence or launches Codex.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import tkinter as tk
import tracemalloc
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psutil
from apm.core.events import Normalizer
from apm.evidence.capsule import Capsule, export_session
from apm.evidence.compare import compare
from apm.storage.memory import Memory
from apm.ui.capsule_window import CapsuleWindow


def run(count):
    if not 2 <= count <= 996:
        raise ValueError('Use 2–996 synthetic command records per session')
    root = Path(__file__).resolve().parents[1]
    directory = root / 'reports' / ('capsule-qualification-' + str(uuid4()))
    directory.mkdir(parents=True)
    database = directory / 'synthetic.sqlite3'
    sessions, case = [str(uuid4()), str(uuid4())], str(uuid4())
    with Memory(database) as memory:
        for side, session in enumerate(sessions):
            normalizer = Normalizer(session, 'synthetic-capsule-demo')
            stream = str(uuid4())
            for start in range(0, count, 32):
                entries = []
                for i in range(start, min(start+32, count)):
                    event = normalizer.normalize(dict(source='codex', category='command', action='STOP',
                        status='synthetic', interpretation_level='synthetic', target='synthetic engineering check',
                        metadata=dict(codex_event='item.completed', item_id='item_0' if i < 2 and side == 0 else 'item_'+str(i),
                                      comparison_key='controlled-fixture', exit_code=0 if i == 0 and side == 0 else 1)))
                    entries.append(dict(event=event.to_dict(), stream=stream, sequence=i+1))
                memory.append_batch(entries)
            unknown = normalizer.normalize(dict(source='fixture', category='verification', action='UNKNOWN',
                status='synthetic', interpretation_level='synthetic', target='Synthetic missing source-time scenario'))
            memory.append(unknown.to_dict(), stream, count+1)
            memory.save_investigation(memory.investigate(session))
            memory.note(session, 'Synthetic human-opinion fixture, excluded by default')
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    exports, imports, paths = [], [], []
    tracemalloc.start()
    rss = [psutil.Process().memory_info().rss]
    for side, session in enumerate(sessions):
        for sample in range(3):
            path = directory / f'session-{side}-sample-{sample}.apmcapsule'
            started = time.perf_counter()
            export_session(database, session, case, path)
            exports.append(time.perf_counter()-started)
            started = time.perf_counter(); capsule = Capsule.open(path)
            imports.append(time.perf_counter()-started)
            rss.append(psutil.Process().memory_info().rss)
            if sample == 0:
                paths.append(path)
    _, python_peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    left, right = [Capsule.open(p) for p in paths]
    started = time.perf_counter(); comparison = compare(left, right)
    compare_seconds = time.perf_counter()-started
    assert comparison['matched_groups'] == 1 and comparison['contradiction_groups'] == 1
    for side, capsule in [('left', left), ('right', right)]:
        for finding in comparison['findings']:
            assert all(capsule.resolve(r['evidence_id']) for r in finding['supporting_evidence'][side])
    child = subprocess.run([sys.executable, '-m', 'apm', 'capsule', 'verify', str(paths[0]), '--expected-sha256', left.sha256],
        cwd=root, capture_output=True, text=True, timeout=15, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    assert child.returncode == 0 and json.loads(child.stdout)['records'] == count+2
    window_root = tk.Tk(); window_root.withdraw()
    pages, citations = [], 0
    try:
        window = CapsuleWindow(window_root, left)
        while True:
            pages.append(len(window.rows))
            for record in list(window.rows.values()):
                if record['references']:
                    window.tree.selection_set(record['event_id']); window_root.update()
                    for ref in record['references']:
                        window.refs.set(ref); window.open_reference()
                        assert ref in window.details.get('1.0', 'end'); citations += 1
            if str(window.next['state']) == 'disabled':
                break
            window.next.invoke()
        window.show_comparison(right)
        assert 'INSUFFICIENT EVIDENCE' in window.details.get('1.0', 'end')
    finally:
        window_root.destroy()
    assert before == hashlib.sha256(database.read_bytes()).hexdigest()
    assert sum(pages) == count+2
    result = dict(workload='SYNTHETIC; no Codex/provider/network operation', command_records_per_session=count,
        sessions=2, source_records=2*(count+3), capsule_records_each=count+2,
        omitted_human_records_each=1, payload_bytes=[p.stat().st_size for p in paths],
        capsule_sha256=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],
        database_unchanged=True, isolated_process_verification=True,
        matched_groups=comparison['matched_groups'], contradiction_groups=comparison['contradiction_groups'],
        native_widget_page_sizes=pages, native_citations_opened=citations, native_comparison_rendered=True,
        visible_gui_inspection=False,
        measurement=dict(samples_each=6, export_seconds=exports, import_seconds=imports,
            export_median_seconds=statistics.median(exports), import_median_seconds=statistics.median(imports),
            comparison_seconds=compare_seconds, python_traced_peak_bytes=python_peak,
            rss_samples_bytes=rss, note='Tracemalloc enabled during export/import; Python peak excludes SQLite/native allocations. RSS is sampled, not a peak guarantee.'),
        environment=dict(python=platform.python_version(),os=platform.system(),machine=platform.machine(),
                         logical_cpus=psutil.cpu_count(),ram_bytes=psutil.virtual_memory().total))
    (directory/'result.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    (directory/'comparison.json').write_text(json.dumps(comparison,indent=2),encoding='utf8')
    print(directory/'result.json')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records',type=int,default=120)
    run(parser.parse_args().records)
