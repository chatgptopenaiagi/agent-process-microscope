"""Fresh-process regression probe. Never suppresses Tk finalization diagnostics."""
import gc
import json
from pathlib import Path
import sys
import threading
import time
import tkinter as tk
import weakref

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apm.ui.holmes_window import HolmesWindow
from apm.ui.main_window import APMWindow
from apm.ui.memory_window import MemoryWindow
from apm.ui.qualification_window import QualificationWindow
from fixture_support import SyntheticDirectory


def pump(root, predicate):
    deadline = time.monotonic() + 10
    while not predicate() and time.monotonic() < deadline:
        root.update()
        time.sleep(.005)
    assert predicate(), 'Bounded GUI operation did not finish'


def cycle(directory, mode):
    root = tk.Tk(); root.withdraw()
    window = HolmesWindow(root, data_root=directory / 'unused', producer_class='SYNTHETIC')
    variables = [weakref.ref(v) for v in vars(window).values() if isinstance(v, tk.Variable)]
    ref = weakref.ref(window)
    def denied():
        raise PermissionError('synthetic inaccessible location')
    def callback_error(_):
        raise ValueError('synthetic callback rejection')
    if mode == 'permission':
        window.submit(denied, lambda _: None)
    elif mode == 'capsule':
        bad = directory / 'malformed.apmcapsule'
        bad.write_text('{"execute":"never"}', encoding='utf-8')
        window.open_capsule(bad)
    elif mode == 'journal':
        window.open_journal(directory / 'absent.sqlite3')
    else:
        window.submit(lambda: None, callback_error)
    pump(root, lambda: not window.busy)
    assert window.operation_status == 'FAIL'
    window.close()
    assert window.closed and window.callback is None and window.future is None
    del window, root
    assert ref() is None, 'Closed window retained by a traceback or callback cycle'
    assert all(r() is None for r in variables), 'Tk variables outlive their owner'


def main():
    # Disable automatic GC only to make the dangerous collection timing deterministic.
    # Original __del__ always runs; stderr is preserved and checked by the parent.
    gc.disable()
    owner = threading.get_ident()
    threads = []
    original = tk.Variable.__del__
    def traced(variable):
        threads.append(threading.get_ident())
        original(variable)
    tk.Variable.__del__ = traced
    try:
        with SyntheticDirectory() as name:
            for _ in range(3):
                for mode in ('permission', 'capsule', 'journal', 'callback'):
                    cycle(Path(name), mode)
                    worker = threading.Thread(target=gc.collect, name='synthetic-background-gc')
                    worker.start(); worker.join(15)
                    assert not worker.is_alive(), 'Background collection timed out'
            root = tk.Tk(); root.withdraw()
            window = APMWindow(root)
            ref = weakref.ref(window)
            window.search_var.set('synthetic deferred filter')
            window.close()
            del window, root
            assert ref() is None, 'Microscope variable traces retain the closed owner'
            for cls in (MemoryWindow, QualificationWindow):
                root = tk.Tk(); root.withdraw()
                window = cls(root, Path(name) / 'absent-evidence.sqlite3')
                ref = weakref.ref(window)
                pump(root, lambda: not window.busy)
                window.close()
                pump(root, lambda: window.closed)
                del window, root
                assert ref() is None, 'Review callback retained its closed owner'
            gc.collect()
        assert threads and all(t == owner for t in threads), 'Tk finalized outside owner'
        print(json.dumps(dict(status='PASS', sequential_holmes_windows=12,
                              variable_finalizers=len(threads), all_on_owner=True)))
    finally:
        gc.collect()  # Failure cleanup also remains on the owner.
        tk.Variable.__del__ = original
        gc.enable()


if __name__ == '__main__':
    main()
