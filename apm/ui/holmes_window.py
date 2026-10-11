"""Native Holmes Lab. Worker owns file/SQL operations; Tk owns presentation."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk
from uuid import uuid4

from apm.holmes.journal import Journal
from apm.holmes.model import Catalog, STATES, text
from apm.holmes.report import export_report, readable_challenge


class HolmesWindow:
    def __init__(self, root, *, producer_class='HUMAN_RECORDED'):
        self.root, self.catalog = root, Catalog()
        self.producer_class = producer_class
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='APM-Holmes')
        self.future = None
        self.closed, self.busy = False, False
        self.path = None
        self.case_id = str(uuid4())
        self.current = None
        self.support, self.contradict = [], []
        self.after, self.page_stack = 0, []
        self.history_after, self.history_stack = 0, []
        self.page_records = {}
        self.entries = {}
        root.title('APM Holmes Lab — evidence and interpretations')
        root.geometry('1180x880')
        self.status = tk.StringVar(value='Create or open an investigation journal, then open selected evidence capsules.')
        self.capsule_sha = tk.StringVar()
        self.title = tk.StringVar(value='New investigation')
        self.purpose = tk.StringVar(value='Understand the evidence and what remains unknown.')
        self.producer = tk.StringVar(value='Local reviewer (declared identity)')
        self.review_state = tk.StringVar(value='INSUFFICIENT_EVIDENCE')
        bar = ttk.Frame(root, padding=8); bar.pack(fill='x')
        for label, fn in [('New journal…', self.choose_new), ('Open journal…', self.choose_journal),
                          ('Open capsule…', self.choose_capsule), ('New hypothesis', self.new_hypothesis),
                          ('Export report…', self.choose_report), ('Backup…', self.choose_backup)]:
            ttk.Button(bar, text=label, command=fn).pack(side='left', padx=3)
        ttk.Label(root, text='Local interpretations only. Sources are read-only. Human assessments authorize no actions.', padding=6).pack(fill='x')
        ttk.Label(root, textvariable=self.status, wraplength=1100, padding=6).pack(fill='x')
        notebook = ttk.Notebook(root); notebook.pack(fill='both', expand=True, padx=8, pady=8)
        evidence = ttk.Frame(notebook, padding=8)
        lab = ttk.Frame(notebook, padding=8)
        history = ttk.Frame(notebook, padding=8)
        advanced = ttk.Frame(notebook, padding=8)
        for frame, label in [(lab, 'Holmes Lab'), (evidence, 'Select evidence'), (history, 'Revision history'), (advanced, 'Advanced JSON')]:
            notebook.add(frame, text=label)
        form = ttk.Frame(lab); form.pack(fill='x')
        for row, (label, var) in enumerate([('Case title', self.title), ('Purpose', self.purpose), ('Declared reviewer', self.producer)]):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky='w')
            ttk.Entry(form, textvariable=var).grid(row=row, column=1, sticky='ew', padx=6, pady=2)
        form.columnconfigure(1, weight=1)
        self.hypotheses = ttk.Treeview(lab, columns=('claim', 'state', 'revision'), show='headings', height=4)
        for col, width in [('claim', 650), ('state', 240), ('revision', 70)]:
            self.hypotheses.heading(col, text=col.title()); self.hypotheses.column(col, width=width)
        self.hypotheses.pack(fill='x', pady=6)
        self.hypotheses.bind('<<TreeviewSelect>>', self.select_hypothesis)
        fields = ttk.Frame(lab); fields.pack(fill='x')
        self.claim = self._field(fields, 'Proposed explanation', 0)
        self.uncertainty = self._field(fields, 'What remains uncertain?', 1)
        self.alternatives = self._field(fields, 'Alternative explanations (one per line)', 2)
        self.missing = self._field(fields, 'Missing evidence (one per line)', 3)
        self.checks = self._field(fields, 'Proposed checks — never executed (one per line)', 4)
        self.reference_status = tk.StringVar(value='Supporting: 0 | Contradicting: 0')
        ttk.Label(lab, textvariable=self.reference_status).pack(anchor='w')
        citebar = ttk.Frame(lab); citebar.pack(fill='x')
        self.citation_choice = ttk.Combobox(citebar, state='readonly', width=75)
        self.citation_choice.pack(side='left', fill='x', expand=True)
        ttk.Button(citebar, text='Resolve saved citation', command=self.resolve_citation).pack(side='left')
        actions = ttk.Frame(lab); actions.pack(fill='x', pady=5)
        for label, fn in [('Create hypothesis', self.propose), ('Save revised hypothesis', self.revise),
                          ('Challenge evidence', self.challenge), ('Find reviewed patterns', self.find_patterns),
                          ('Clear draft references', self.clear_references)]:
            ttk.Button(actions, text=label, command=fn).pack(side='left', padx=3)
        review = ttk.Frame(lab); review.pack(fill='x')
        ttk.Combobox(review, textvariable=self.review_state, values=STATES, state='readonly', width=29).pack(side='left')
        self.reason = ttk.Entry(review); self.reason.pack(side='left', fill='x', expand=True, padx=4)
        self.reason.insert(0, 'Explain the assessment or correction here.')
        ttk.Button(review, text='Record assessment', command=lambda: self.review(False)).pack(side='left')
        ttk.Button(review, text='Correct assessment', command=lambda: self.review(True)).pack(side='left', padx=3)
        self.summary = tk.Text(lab, height=10, wrap='word'); self.summary.pack(fill='both', expand=True, pady=6)
        self.capsules = ttk.Combobox(evidence, textvariable=self.capsule_sha, state='readonly', width=90)
        self.capsules.pack(fill='x'); self.capsules.bind('<<ComboboxSelected>>', lambda e: self.load_page(reset=True))
        self.evidence = ttk.Treeview(evidence, columns=('arrival', 'source', 'class', 'event', 'outcome'), show='headings', height=12)
        for col in ('arrival', 'source', 'class', 'event', 'outcome'):
            self.evidence.heading(col, text=col.title())
        self.evidence.pack(fill='both', expand=True, pady=6)
        self.evidence.bind('<<TreeviewSelect>>', self.select_evidence)
        buttons = ttk.Frame(evidence); buttons.pack(fill='x')
        for label, fn in [('Previous 100', self.previous_page), ('Next 100', self.next_page),
                          ('Use as support', lambda: self.attach('support')), ('Use as contradiction', lambda: self.attach('contradict'))]:
            ttk.Button(buttons, text=label, command=fn).pack(side='left', padx=4)
        self.evidence_summary = tk.Text(evidence, height=10, wrap='word'); self.evidence_summary.pack(fill='both', expand=True, pady=8)
        self.history = ttk.Treeview(history, columns=('revision', 'kind', 'state', 'producer'), show='headings')
        for col in ('revision', 'kind', 'state', 'producer'):
            self.history.heading(col, text=col.title())
        self.history.pack(fill='both', expand=True)
        self.history.bind('<<TreeviewSelect>>', self.select_revision)
        nav = ttk.Frame(history); nav.pack(fill='x')
        ttk.Button(nav, text='Previous 100 revisions', command=self.previous_history).pack(side='left')
        ttk.Button(nav, text='Next 100 revisions', command=self.next_history).pack(side='left')
        self.history_summary = tk.Text(history, height=10, wrap='word'); self.history_summary.pack(fill='both', expand=True)
        self.raw = tk.Text(advanced, wrap='word'); self.raw.pack(fill='both', expand=True)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.timer = root.after(30, self.poll)

    @staticmethod
    def _field(parent, label, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='nw', padx=3, pady=2)
        widget = tk.Text(parent, height=2, wrap='word'); widget.grid(row=row, column=1, sticky='ew', pady=2)
        parent.columnconfigure(1, weight=1)
        return widget

    @staticmethod
    def put(widget, value):
        widget.configure(state='normal'); widget.delete('1.0', 'end'); widget.insert('1.0', value); widget.configure(state='disabled')

    def submit(self, operation, callback):
        if self.busy or self.closed:
            self.status.set('Please wait for the current bounded operation to finish.'); return
        self.busy = True; self.status.set('Working locally…')
        self.callback = callback
        self.future = self.executor.submit(operation)

    def poll(self):
        if self.closed:
            return
        if self.future is not None and self.future.done():
            future, self.future = self.future, None
            self.busy = False
            try:
                result = future.result()
                self.status.set('Ready. Source evidence unchanged; no execution authority.')
                self.callback(result)
            except Exception:
                # Do not display exception text potentially containing a private path or input.
                self.status.set('Operation rejected or unavailable. Check citations, field limits, review selection and destination. Sources unchanged.')
        self.timer = self.root.after(30, self.poll)

    def choose_new(self):
        path = filedialog.asksaveasfilename(parent=self.root, title='Create a NEW investigation journal', defaultextension='.sqlite3')
        if path: self.open_journal(path, create=True)

    def choose_journal(self):
        path = filedialog.askopenfilename(parent=self.root, title='Open Holmes journal', filetypes=[('Holmes journal', '*.sqlite3')])
        if path: self.open_journal(path)

    def open_journal(self, path, create=False):
        path = Path(path)
        def work():
            with (Journal.create(path) if create else Journal(path)) as journal:
                return journal.all_entries(), journal.verify()
        def done(result):
            self.path = path; self.current = None
            self.refresh(result[0])
            self.status.set(f"Journal checks passed: {result[1]['entries']} revisions; tip {result[1]['tip']}. Unkeyed, identity unverified.")
        self.submit(work, done)

    def choose_capsule(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[('Evidence capsule', '*.apmcapsule')])
        if path: self.open_capsule(path)

    def open_capsule(self, path):
        def done(sha):
            self.capsules.configure(values=[s['sha256'] for s in self.catalog.summaries()])
            self.capsule_sha.set(sha); self.load_page(reset=True)
        self.submit(lambda: self.catalog.open(path), done)

    def load_page(self, reset=False):
        if reset: self.after, self.page_stack = 0, []
        sha, after = self.capsule_sha.get(), self.after
        if not sha: return
        def done(page):
            self.page_records = {r['event_id']: r for r in page}
            self.evidence.delete(*self.evidence.get_children())
            for r in page:
                self.evidence.insert('', 'end', iid=r['event_id'], values=(r['arrival'], r['source'],
                    r['evidence_class'] + ' (declared)', r['category'] + ' ' + r['action'], r['attributes'].get('exit_code', 'UNKNOWN')))
            self.status.set(f"{len(page)} records on this page. Internal capsule hashes checked; exporter provenance unverified.")
        self.submit(lambda: self.catalog.page(sha, after), done)

    def next_page(self):
        if self.busy or not self.page_records: return
        self.page_stack.append(self.after); self.after = list(self.page_records.values())[-1]['arrival']; self.load_page()

    def previous_page(self):
        if self.busy or not self.page_stack: return
        self.after = self.page_stack.pop(); self.load_page()

    def select_evidence(self, event=None):
        selection = self.evidence.selection()
        if not selection: return
        r = self.page_records[selection[0]]
        self.put(self.evidence_summary, f"{r['source']} declares {r['category']} / {r['action']}.\nEvidence category: {r['evidence_class']} (exporter declaration).\nExit code: {r['attributes'].get('exit_code', 'UNKNOWN')}\nEvent: {r['event_id']}\nReceipt position: {r['arrival']}. Clock uncertainty UNKNOWN; this is not causal order.")
        self.put(self.raw, json.dumps(r, indent=2))

    def attach(self, role):
        if self.busy: return
        selected = self.evidence.selection()
        if not selected: return
        ref = self.catalog.make_ref(self.capsule_sha.get(), selected[0])
        target = getattr(self, role)
        if ref not in target and len(target) < 40: target.append(ref)
        self.reference_status.set(f'Supporting: {len(self.support)} | Contradicting: {len(self.contradict)}')

    def clear_references(self):
        self.support, self.contradict = [], []
        self.reference_status.set('Supporting: 0 | Contradicting: 0')

    def resolve_citation(self):
        index = self.citation_choice.current()
        if index < 0 or not self.current: return
        references = self.current['hypothesis']['support'] + self.current['hypothesis']['contradict']
        ref = references[index]
        def done(record):
            self.put(self.summary, f"Resolved {ref['evidence_id']}\nCapsule {ref['capsule_sha256']}\nSession {ref['session_id']}\n{record['source']} declares {record['category']} / {record['action']} [{record['evidence_class']}].\nExit code: {record['attributes'].get('exit_code', 'UNKNOWN')}\nThis lookup verifies reference resolution, not the truth or relevance of the reported fact.")
            self.put(self.raw, json.dumps(record, indent=2))
        self.submit(lambda: self.catalog.resolve(ref), done)

    def find_patterns(self):
        if not self.path: return
        from apm.holmes.patterns import retrieve
        path = self.path
        def work():
            with Journal(path) as journal: return retrieve(journal, self.catalog)
        def done(result):
            lines = [f"{p['description']}: {p['matched_records']} matches. {p['conclusion']}" for p in result['patterns']]
            self.put(self.summary, '\n\n'.join(lines) or 'No active human-reviewed patterns in this journal. Patterns are never promoted automatically.')
            self.put(self.raw, json.dumps(result, indent=2))
        self.submit(work, done)

    def new_hypothesis(self):
        if self.busy: return
        self.current = None; self.clear_references()
        self.hypotheses.selection_remove(*self.hypotheses.selection())
        for widget in (self.claim, self.uncertainty, self.alternatives, self.missing, self.checks):
            widget.delete('1.0', 'end')
        self.put(self.summary, 'Write an explanation, its uncertainty and alternatives. Select evidence on the next tab, then create the hypothesis.')

    def draft(self):
        def lines(widget):
            return [text(v) for v in widget.get('1.0', 'end').splitlines() if v.strip()]
        missing = lines(self.missing)
        retained = self.current['hypothesis']['missing'] if self.current else []
        # Never reassign an old scoped reference to a different, edited missing claim.
        missing_items = []
        for reason in missing:
            original = next((v for v in retained if v['reason'] == reason), None)
            missing_items.append(dict(reference=original['reference'] if original else None, reason=reason))
        return dict(claim=text(self.claim.get('1.0', 'end')), uncertainty=text(self.uncertainty.get('1.0', 'end')),
            alternatives=lines(self.alternatives), missing=missing_items,
            checks=lines(self.checks), support=list(self.support), contradict=list(self.contradict))

    def change(self, operation):
        if self.path is None:
            self.status.set('Create or open a journal first.'); return
        path = self.path
        def work():
            with Journal(path) as journal:
                value = operation(journal)
                return value, journal.all_entries()
        def done(result):
            self.current = result[0]; self.refresh(result[1])
            self.hypotheses.selection_set(self.current['hypothesis_id']); self.select_hypothesis()
        self.submit(work, done)

    def propose(self):
        try:
            value, producer, title, purpose = self.draft(), text(self.producer.get(), 200), text(self.title.get()), text(self.purpose.get())
        except ValueError:
            self.status.set('Enter a claim, uncertainty and valid bounded fields.'); return
        case_id, request_id = self.case_id, str(uuid4())
        self.change(lambda j: j.propose(case_id, title, purpose, producer, value, self.catalog,
                                       request_id=request_id, producer_class=self.producer_class))

    def update(self, kind, detail):
        if not self.current:
            self.status.set('Select a saved hypothesis first.'); return
        current, producer, request_id = self.current, text(self.producer.get(), 200), str(uuid4())
        self.change(lambda j: j.revise(current['hypothesis_id'], current['revision'], producer, kind, detail,
                                      self.catalog, request_id=request_id, producer_class=self.producer_class))

    def revise(self):
        try: self.update('REVISE', dict(hypothesis=self.draft(), reason=text(self.reason.get())))
        except ValueError: self.status.set('Enter a claim, uncertainty and revision reason.')

    def challenge(self):
        try: self.update('CHALLENGE', {})
        except ValueError: self.status.set('Enter a declared reviewer.')

    def review(self, correction=False):
        try: self.update('CORRECT' if correction else 'REVIEW', dict(state=self.review_state.get(), reason=text(self.reason.get())))
        except ValueError: self.status.set('Enter an assessment reason and declared reviewer.')

    def refresh(self, entries):
        self.entries = {e['sequence']: e for e in entries}
        latest = {e['hypothesis_id']: e for e in entries}
        self.hypotheses.delete(*self.hypotheses.get_children())
        for key, entry in latest.items():
            self.hypotheses.insert('', 'end', iid=key, values=(entry['hypothesis']['claim'], entry['state'], entry['revision']))
        self.latest = latest
        self.history_after, self.history_stack = 0, []
        self.show_history()

    def select_hypothesis(self, event=None):
        if self.busy: return
        selected = self.hypotheses.selection()
        if not selected: return
        e = self.latest[selected[0]]; self.current = e; self.case_id = e['case_id']
        self.title.set(e['title']); self.purpose.set(e['purpose'])
        h = e['hypothesis']; self.support, self.contradict = list(h['support']), list(h['contradict'])
        self.citation_choice.configure(values=[role + ': ' + r['evidence_id'] + ' / ' + r['capsule_sha256'][:12]
                                              for role in ('support', 'contradict') for r in h[role]])
        self.citation_choice.set('')
        for widget, value in [(self.claim, h['claim']), (self.uncertainty, h['uncertainty']),
            (self.alternatives, '\n'.join(h['alternatives'])), (self.missing, '\n'.join(v['reason'] for v in h['missing'])),
            (self.checks, '\n'.join(h['checks']))]:
            widget.delete('1.0', 'end'); widget.insert('1.0', value)
        self.reference_status.set(f'Supporting: {len(self.support)} | Contradicting: {len(self.contradict)}')
        self.put(self.summary, readable_challenge(e['detail']) if e['kind'] == 'CHALLENGE' else
                 f"Review state: {e['state']}\n{h['claim']}\n\nUncertainty: {h['uncertainty']}\n\n{e['detail'].get('reason', 'Run Challenge evidence to inspect limits.')}\n\nInterpretation only. No execution permission.")
        self.put(self.raw, json.dumps(e, indent=2))

    def show_history(self):
        self.history.delete(*self.history.get_children())
        for seq, e in list((s, e) for s, e in self.entries.items() if s > self.history_after)[:100]:
            self.history.insert('', 'end', iid=str(seq), values=(e['revision'], e['kind'], e['state'], e['producer']))

    def next_history(self):
        rows = self.history.get_children()
        if rows: self.history_stack.append(self.history_after); self.history_after = int(rows[-1]); self.show_history()

    def previous_history(self):
        if self.history_stack: self.history_after = self.history_stack.pop(); self.show_history()

    def select_revision(self, event=None):
        selected = self.history.selection()
        if not selected: return
        e = self.entries[int(selected[0])]
        self.put(self.history_summary, f"Revision {e['revision']} — {e['kind']} — {e['state']}\n{e['hypothesis']['claim']}\n\n{e['detail'].get('reason', '')}\n\nUncertainty: {e['hypothesis']['uncertainty']}\nEarlier revisions remain unchanged.")
        self.put(self.raw, json.dumps(e, indent=2))

    def choose_report(self):
        path = filedialog.asksaveasfilename(parent=self.root, title='New minimized case report', defaultextension='.html', filetypes=[('HTML', '*.html'), ('JSON', '*.json')])
        if path: self.export(path)

    def export(self, destination):
        if not self.path: return
        path, case_id = self.path, self.case_id
        def work():
            with Journal(path) as journal: return export_report(journal, self.catalog, case_id, destination)
        self.submit(work, lambda result: self.status.set(f"Report written: {result['revisions']} revisions, {result['citations']} cited records. No execution authority."))

    def choose_backup(self):
        if not self.path: return
        destination = filedialog.asksaveasfilename(parent=self.root, title='New journal backup', defaultextension='.sqlite3')
        if not destination: return
        path = self.path
        def work():
            with Journal(path) as journal: return journal.backup(destination)
        self.submit(work, lambda result: self.status.set(f"Backup verified: {result['entries']} entries. Source evidence is separate."))

    def close(self):
        self.closed = True
        self.root.after_cancel(self.timer)
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()
