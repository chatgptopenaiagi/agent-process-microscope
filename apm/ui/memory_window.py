"""Optional 2D telescope: sessions -> evidence -> deterministic investigation."""
from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from tkinter import ttk

from apm.storage.memory import Memory, explanation


from apm.ui.ownership import owner_thread_only


@owner_thread_only
class MemoryWindow:
    def __init__(self, root, path):
        self.root, self.path = root, path
        self.busy, self.closed, self.cursor = False, False, 0
        self.results = queue.Queue(maxsize=1)
        self.worker = self.callback = self.close_timer = None
        self.closing = False
        self.records = {}
        root.title('APM — Memory and investigation')
        root.geometry('1100x750')
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.session = tk.StringVar(root)
        self.search = tk.StringVar(root)
        self.status = tk.StringVar(root, 'Local evidence only. ASK uses deterministic rules; no model or cloud connection.')
        self.watch = tk.BooleanVar(root, False)
        self.note_text = tk.StringVar(root)
        self.decision = tk.StringVar(root, 'annotate')
        frame = ttk.Frame(root, padding=12); frame.pack(fill='both', expand=True)
        bar = ttk.Frame(frame); bar.pack(fill='x')
        ttk.Button(bar, text='Refresh sessions', command=self.refresh_sessions).pack(side='left')
        self.sessions = ttk.Combobox(bar, textvariable=self.session, state='readonly', width=40)
        self.sessions.pack(side='left', padx=5)
        self.sessions.bind('<<ComboboxSelected>>', lambda _: self.load_events(reset=True))
        ttk.Button(bar, text='Ask / investigate', command=self.ask).pack(side='left')
        ttk.Checkbutton(bar, text='Watch arrivals', variable=self.watch).pack(side='left')
        filters = ttk.Frame(frame); filters.pack(fill='x', pady=8)
        ttk.Entry(filters, textvariable=self.search).pack(side='left', fill='x', expand=True)
        ttk.Button(filters, text='Search from start', command=lambda: self.load_events(reset=True)).pack(side='left')
        ttk.Button(filters, text='Next 100', command=self.load_events).pack(side='left')
        self.tree = ttk.Treeview(frame, columns=('class', 'source', 'action', 'target'), show='headings', height=12)
        for col, width in [('class', 130), ('source', 130), ('action', 80), ('target', 560)]:
            self.tree.heading(col, text=col.upper()); self.tree.column(col, width=width)
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.details)
        self.text = tk.Text(frame, height=16, wrap='word'); self.text.pack(fill='both', expand=True, pady=8)
        notes = ttk.Frame(frame); notes.pack(fill='x')
        ttk.Combobox(notes, textvariable=self.decision, values=('annotate','approve','reject','investigate','correct'), state='readonly', width=12).pack(side='left')
        ttk.Entry(notes, textvariable=self.note_text).pack(side='left', fill='x', expand=True)
        ttk.Button(notes, text='Record opinion', command=self.record_note).pack(side='left')
        ttk.Label(frame, text='Recorded decisions never execute actions or grant permissions. Select an event to cite it.').pack(anchor='w')
        ttk.Label(frame, textvariable=self.status, wraplength=1000).pack(anchor='w', pady=8)
        self.timer = root.after(150, self.tick)
        self.refresh_sessions()

    def work(self, operation, callback, *, write=False):
        if self.busy or self.closed or self.closing:
            return
        self.busy = True
        self.callback = callback
        path, results = self.path, self.results
        def run():
            try:
                with Memory(path, readonly=not write) as memory:
                    value = operation(memory)
                results.put_nowait((value, None))
            except Exception:
                results.put_nowait((None, 'Memory unavailable; check the selected database, session and storage limits.'))
        self.worker = threading.Thread(target=run, name='APM memory query', daemon=True)
        self.worker.start()

    def refresh_sessions(self):
        def show(rows):
            self.sessions['values'] = [r['session_id'] for r in rows]
            if rows and self.session.get() not in self.sessions['values']:
                self.session.set(rows[0]['session_id'])
            self.status.set(f'{len(rows)} sessions listed (maximum 100). Select a session, then Ask or Next 100.')
        self.work(lambda m: m.sessions(), show)

    def load_events(self, reset=False):
        if self.busy or not self.session.get():
            return
        session, search = self.session.get(), self.search.get()
        after = 0 if reset else self.cursor
        def show(rows):
            if reset:
                self.cursor = 0
            if rows or reset:
                self.tree.delete(*self.tree.get_children())
                self.records = {str(r['arrival']): r for r in rows}
                for row in rows:
                    event = row['event']
                    self.tree.insert('', 'end', iid=str(row['arrival']), values=(row['evidence_class'], event['source'], event['action'], event['target']))
                if rows:
                    self.cursor = rows[-1]['arrival']
            self.status.set(f'{len(rows)} matching arrivals in this page; cursor {self.cursor}. Receipt order does not establish causation.')
        self.work(lambda m: m.events(session, after=after, search=search), show)

    def show_text(self, value):
        self.text.configure(state='normal'); self.text.delete('1.0', 'end')
        self.text.insert('1.0', value); self.text.configure(state='disabled')

    def details(self, _=None):
        selected = self.tree.selection()
        if selected:
            self.show_text(json.dumps(self.records[selected[0]], indent=2))

    def ask(self):
        session = self.session.get()
        if session:
            def investigate(memory):
                result = memory.investigate(session)
                memory.save_investigation(result)
                return result
            self.work(investigate, lambda value: self.show_text(explanation(value)), write=True)

    def record_note(self):
        session, text, decision = self.session.get(), self.note_text.get(), self.decision.get()
        selected = self.tree.selection()
        refs = [self.records[selected[0]]['event']['event_id']] if selected else []
        if session and text:
            self.work(lambda m: m.note(session, text, decision=decision, references=refs),
                      lambda _: (self.note_text.set(''), self.status.set('Opinion recorded; no action authorized or executed.')), write=True)

    def tick(self):
        if self.closed or self.closing:
            return
        try:
            value, error = self.results.get_nowait()
            callback, self.callback = self.callback, None
            self.busy = False
            if error:
                self.status.set(error)
            else:
                callback(value)
        except queue.Empty:
            pass
        if self.watch.get() and not self.busy:
            self.load_events()
        self.timer = self.root.after(500, self.tick)

    def finish_close(self):
        self.close_timer = None
        self.close()

    def close(self):
        if self.closed:
            return
        self.closing = True
        self.root.after_cancel(self.timer)
        if self.worker is not None and self.worker.is_alive():
            self.status.set('Finishing the local operation before closing…')
            if self.close_timer is None:
                self.close_timer = self.root.after(25, self.finish_close)
            return
        if self.worker is not None:
            self.worker.join()
        if self.close_timer is not None:
            self.root.after_cancel(self.close_timer)
            self.close_timer = None
        self.callback = None
        while not self.results.empty():
            self.results.get_nowait()
        self.closed = True
        self.root.destroy()
