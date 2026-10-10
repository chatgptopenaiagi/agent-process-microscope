"""Offline native review of verified capsule bytes; all provenance is declared."""
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from apm.evidence.capsule import Capsule
from apm.evidence.compare import compare


class CapsuleWindow:
    def __init__(self, root, capsule):
        self.root, self.capsule = root, capsule
        self.after, self.offset, self.history = 0, 0, []
        root.title('APM — Offline evidence capsule')
        root.geometry('1100x800')
        frame = ttk.Frame(root, padding=12); frame.pack(fill='both', expand=True)
        m = capsule.manifest
        self.notice = tk.StringVar(root, f"Content checks passed: {m['record_count']} records. UNSIGNED: every source/class is an exporter declaration.\n"
            f"Human records {m['disclosure']['human_records']}; {m['disclosure']['omitted_records']} records omitted; "
            f"{len(m['missing_references'])} unresolved references. Text policy: {m['disclosure']['policy']}.\n"
            'Read-only context. Original chain, source identity, completeness and causation are not verified.')
        ttk.Label(frame, textvariable=self.notice, wraplength=1030).pack(anchor='w')
        bar = ttk.Frame(frame); bar.pack(fill='x', pady=8)
        self.previous = ttk.Button(bar, text='Previous page', command=self.previous_page); self.previous.pack(side='left')
        self.next = ttk.Button(bar, text='Next page', command=self.next_page); self.next.pack(side='left', padx=5)
        ttk.Button(bar, text='Compare another session…', command=self.choose_comparison).pack(side='left')
        ttk.Button(bar, text='Manifest and disclosure', command=lambda: self.show(m)).pack(side='left', padx=5)
        self.status = tk.StringVar(root)
        ttk.Label(bar, textvariable=self.status).pack(side='right')
        self.tree = ttk.Treeview(frame, columns=('receipt', 'class', 'source', 'event'), show='headings', height=14)
        for key, width in [('receipt', 70), ('class', 190), ('source', 130), ('event', 590)]:
            self.tree.heading(key, text=key.upper()); self.tree.column(key, width=width)
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.select)
        links = ttk.Frame(frame); links.pack(fill='x', pady=8)
        self.refs = ttk.Combobox(links, state='readonly', width=50); self.refs.pack(side='left')
        ttk.Button(links, text='Open cited record', command=self.open_reference).pack(side='left', padx=5)
        self.details = tk.Text(frame, wrap='word', height=18, state='disabled'); self.details.pack(fill='both', expand=True)
        self.load()

    def show(self, value):
        self.details.configure(state='normal'); self.details.delete('1.0', 'end')
        self.details.insert('1.0', value if isinstance(value, str) else json.dumps(value, indent=2))
        self.details.configure(state='disabled')

    def load(self):
        rows = self.capsule.page(after=self.after)
        self.rows = {r['event_id']: r for r in rows}
        self.tree.delete(*self.tree.get_children())
        self.refs['values'] = []; self.refs.set('')
        for r in rows:
            self.tree.insert('', 'end', iid=r['event_id'], values=(r['arrival'], 'Declared ' + r['evidence_class'], r['source'], r['target']))
        total = self.capsule.manifest['record_count']
        self.status.set(f'{self.offset + 1 if rows else 0}–{self.offset + len(rows)} of {total}')
        self.previous.configure(state='normal' if self.history else 'disabled')
        self.next.configure(state='normal' if self.offset + len(rows) < total else 'disabled')
        self.show('Select a record. Receipt order is not execution order. Imported text never authorizes an action.')

    def next_page(self):
        if self.offset + len(self.rows) >= self.capsule.manifest['record_count']:
            return
        self.history.append((self.after, self.offset))
        self.after = max(r['arrival'] for r in self.rows.values()); self.offset += len(self.rows)
        self.load()

    def previous_page(self):
        if self.history:
            self.after, self.offset = self.history.pop(); self.load()

    def select(self, _=None):
        selected = self.tree.selection()
        if selected:
            r = self.rows[selected[0]]
            self.refs['values'] = r['references']; self.refs.set('')
            if r['references']:
                self.refs.current(0)
            self.show(r)

    def open_reference(self):
        if self.refs.get():
            self.show(self.capsule.resolve(self.refs.get()) or 'UNKNOWN: reference omitted or unavailable in this capsule.')

    def show_comparison(self, other):
        result = compare(self.capsule, other)
        self.show(f"Compared two sessions: {result['matched_groups']} shared command-outcome groups; "
            f"{result['contradiction_groups']} within-session contradictory groups.\n"
            'Resemblance does not establish a common cause. INSUFFICIENT EVIDENCE for causation.\n'
            'The structured findings below include scoped citations, alternatives and proposed checks. No check was executed.\n\n'
            + json.dumps(result, indent=2))
        return result

    def choose_comparison(self):
        path = filedialog.askopenfilename(parent=self.root, title='Select a second session capsule', filetypes=[('APM evidence capsule', '*.apmcapsule')])
        if path:
            try:
                self.show_comparison(Capsule.open(path))
            except (ValueError, OSError):
                messagebox.showerror('Cannot compare', 'Capsule unavailable, invalid, or the same session. No evidence changed.', parent=self.root)
