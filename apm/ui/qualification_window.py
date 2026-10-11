"""Native read-only qualification review; one worker owns the private snapshot."""
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk

from apm.storage.review import QualificationReview, summary_text


from apm.ui.ownership import owner_thread_only


def _worker(path, expected_tip, cancel, jobs, results):
    # No window, bound UI method, callback or Tk variable crosses this boundary.
    try:
        with QualificationReview(path, expected_tip=expected_tip, cancelled=cancel.is_set) as review:
            results.put_nowait((dict(integrity=review.integrity,
                sessions=review.sessions() if review.available else []), None))
            while not cancel.wait(.05):
                try:
                    operation = jobs.get_nowait()
                except queue.Empty:
                    continue
                try:
                    result = (operation(review), None)
                except Exception:
                    result = (None, 'Review unavailable: invalid session, evidence or bounds. No source writes performed.')
                finally:
                    del operation
                if not cancel.is_set():
                    results.put_nowait(result)
                del result
    except Exception:
        if not cancel.is_set():
            results.put_nowait((None, 'Cannot open or verify this database. Unsupported, inaccessible, oversized or cancelled review.'))


@owner_thread_only
class QualificationWindow:
    def __init__(self, root, path, *, session=None, expected_tip=None):
        self.root = root
        self.closed = self.closing = False
        self.close_timer = None
        self.callback = self.loaded
        self.busy = True
        self.cancel = threading.Event()
        self.jobs, self.results = queue.Queue(maxsize=1), queue.Queue(maxsize=1)
        self.records, self.refs = {}, []
        self.history, self.after, self.offset = [], 0, 0
        self.total = 0
        self.session = tk.StringVar(root, session or '')
        self.status = tk.StringVar(root, 'Opening read-only snapshot and verifying integrity…')
        root.title('APM — Read-only qualification review')
        root.geometry('1180x860')
        root.protocol('WM_DELETE_WINDOW', self.close)
        frame = ttk.Frame(root, padding=10); frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='READ ONLY • Fixed snapshot • No notes, execution or source changes').pack(anchor='w')
        bar = ttk.Frame(frame); bar.pack(fill='x', pady=6)
        self.sessions = ttk.Combobox(bar, textvariable=self.session, width=40)
        self.sessions.pack(side='left')
        ttk.Button(bar, text='Review session', command=self.load_session).pack(side='left', padx=5)
        ttk.Label(bar, text='100 recent sessions listed; any session UUID may be entered.').pack(side='left')
        self.summary = tk.Text(frame, height=12, wrap='word', state='disabled')
        self.summary.pack(fill='x')
        pages = ttk.Frame(frame); pages.pack(fill='x', pady=5)
        self.previous = ttk.Button(pages, text='Previous page', command=self.previous_page, state='disabled')
        self.previous.pack(side='left')
        self.next = ttk.Button(pages, text='Next page', command=self.next_page, state='disabled')
        self.next.pack(side='left', padx=5)
        self.tree = ttk.Treeview(frame, columns=('arrival', 'class', 'source', 'action', 'target'), show='headings', height=10)
        for name, width in [('arrival', 65), ('class', 150), ('source', 125), ('action', 70), ('target', 610)]:
            self.tree.heading(name, text=name.upper()); self.tree.column(name, width=width)
        scroll = ttk.Scrollbar(frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y'); self.tree.pack(fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.select_record)
        links = ttk.Frame(frame); links.pack(fill='x', pady=6)
        self.citation = ttk.Combobox(links, state='readonly', width=60)
        self.citation.pack(side='left', fill='x', expand=True)
        ttk.Button(links, text='Open cited evidence', command=self.open_citation).pack(side='left')
        self.details = tk.Text(frame, height=12, wrap='word', state='disabled')
        self.details.pack(fill='both', expand=True)
        ttk.Label(frame, textvariable=self.status, wraplength=1120).pack(anchor='w', pady=5)
        self.worker = threading.Thread(target=_worker, args=(path, expected_tip, self.cancel, self.jobs, self.results), name='APM read-only review', daemon=True)
        self.worker.start()
        self.timer = root.after(50, self.tick)

    @staticmethod
    def set_text(widget, value):
        widget.configure(state='normal'); widget.delete('1.0', 'end')
        widget.insert('1.0', value); widget.configure(state='disabled')


    def work(self, operation, callback):
        if self.busy or self.closed or self.closing:
            return
        self.busy = True
        self.previous.configure(state='disabled'); self.next.configure(state='disabled')
        self.callback = callback
        self.jobs.put_nowait(operation)

    def loaded(self, result):
        integrity = result['integrity']
        if not integrity['ok']:
            self.set_text(self.summary, 'INTEGRITY FAILED. Evidence display disabled.\n' + json.dumps(integrity, indent=2))
            self.status.set('Hash/index/counter verification or supplied expected tip failed; no trustworthy review available.')
            return
        self.sessions['values'] = [r['session_id'] for r in result['sessions']]
        if not self.session.get() and result['sessions']:
            self.session.set(result['sessions'][0]['session_id'])
        self.status.set('Integrity verified for this snapshot. Unkeyed hashes do not authenticate the source. Reopen to refresh.')
        if self.session.get():
            self.load_session()
        else:
            self.set_text(self.summary, f"Empty verified database. Records: 0; tip: {integrity['tip']}")

    def load_session(self):
        if self.busy:
            return
        session = self.session.get()
        # Freeze selected scope; edits in the entry never change an existing page.
        def show(result):
            self.selected_session = session
            self.history, self.after, self.offset = [], 0, 0
            self.total = result['summary']['counts'].get('records', 0)
            self.set_text(self.summary, summary_text(result['summary']))
            self.show_page(result['rows'])
        self.work(lambda r: dict(summary=r.summary(session), rows=r.page(session)), show)

    def show_page(self, rows):
        self.tree.delete(*self.tree.get_children())
        self.records = {str(r['arrival']): r for r in rows}
        self.refs = []; self.citation.set(''); self.citation['values'] = []
        self.set_text(self.details, 'Select a record to inspect it and resolve its saved citations.')
        for row in rows:
            e = row['event']
            self.tree.insert('', 'end', iid=str(row['arrival']), values=(row['arrival'], row['evidence_class'], e['source'], e['action'], e['target']))
        self.status.set(f"Records {self.offset + 1 if rows else 0}–{self.offset + len(rows)} of {self.total}. Receipt order is not execution order or causation.")
        self.controls()

    def controls(self):
        self.previous.configure(state='normal' if self.history and not self.busy else 'disabled')
        self.next.configure(state='normal' if self.offset + len(self.records) < self.total and not self.busy else 'disabled')

    def next_page(self):
        if self.busy or self.offset + len(self.records) >= self.total:
            return
        after = max(int(k) for k in self.records)
        def show(rows):
            self.history.append((self.after, self.offset))
            self.after, self.offset = after, self.offset + len(self.records)
            self.show_page(rows)
        session = self.selected_session
        self.work(lambda r: r.page(session, after=after), show)

    def previous_page(self):
        if self.busy or not self.history:
            return
        after, offset = self.history[-1]
        def show(rows):
            self.history.pop(); self.after, self.offset = after, offset
            self.show_page(rows)
        session = self.selected_session
        self.work(lambda r: r.page(session, after=after), show)

    def select_record(self, _=None):
        selected = self.tree.selection()
        if self.busy or not selected:
            return
        record = self.records[selected[0]]
        def show(value):
            self.refs = value['references']
            self.citation['values'] = [f"{r['evidence_id']} — {r['status']}" for r in self.refs]
            self.citation.set('')
            if self.refs:
                self.citation.current(0)
            self.set_text(self.details, value['checkpoint'] + '\n' + json.dumps(record, indent=2))
        session = self.selected_session
        self.work(lambda r: r.citations(session, record['event']['event_id']), show)

    def open_citation(self):
        index = self.citation.current()
        if 0 <= index < len(self.refs):
            ref = self.refs[index]
            self.set_text(self.details, json.dumps(ref['record'], indent=2) if ref['record'] else ref['status'])

    def tick(self):
        if self.closed or self.closing:
            return
        try:
            value, error = self.results.get_nowait()
            callback, self.callback = self.callback, None
            self.busy = False
            if error:
                self.status.set(error)
            elif callback:
                callback(value)
            self.controls()
        except queue.Empty:
            pass
        self.timer = self.root.after(50, self.tick)

    def finish_close(self):
        self.close_timer = None
        self.close()

    def close(self):
        if self.closed:
            return
        self.closing = True
        self.cancel.set()
        self.root.after_cancel(self.timer)
        if self.worker.is_alive():
            self.status.set('Finishing the read-only operation before closing…')
            if self.close_timer is None:
                self.close_timer = self.root.after(25, self.finish_close)
            return
        self.worker.join()
        if self.close_timer is not None:
            self.root.after_cancel(self.close_timer)
            self.close_timer = None
        self.callback = None
        for pending in (self.jobs, self.results):
            while not pending.empty():
                pending.get_nowait()
        self.closed = True
        self.root.destroy()
