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
    def __init__(self, root, *, producer_class='HUMAN_RECORDED', data_root=None):
        from apm.paths import user_data_root
        self.data_root = user_data_root(data_root)
        self.root, self.catalog = root, Catalog()
        self.producer_class = producer_class
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='APM-Holmes')
        self.future = None
        self.callback = None
        self.closed, self.busy, self.closing = False, False, False
        self.path = None
        self.case_id = str(uuid4())
        self.current = None
        self.support, self.contradict = [], []
        self.after, self.page_stack = 0, []
        self.history_after, self.history_stack = 0, []
        self.page_records = {}
        self.entries = {}
        self.microscopes = []
        root.title('APM — Holmes Lab')
        root.geometry('1160x850')
        root.minsize(900, 680)
        self.status = tk.StringVar(root, value='Start with a synthetic demonstration or open your own case.')
        self.capsule_sha = tk.StringVar(root)
        self.title = tk.StringVar(root, value='New investigation')
        self.purpose = tk.StringVar(root, value='Understand the evidence and what remains unknown.')
        self.producer = tk.StringVar(root, value='Local reviewer (declared identity)')
        self.review_state = tk.StringVar(root, value='INSUFFICIENT_EVIDENCE')
        root.option_add('*Font', ('Segoe UI', 11))
        style = ttk.Style(root)
        style.configure('Holmes.Title.TLabel', font=('Segoe UI', 22, 'bold'))
        style.configure('Holmes.Heading.TLabel', font=('Segoe UI', 14, 'bold'))
        style.configure('Holmes.Primary.TButton', font=('Segoe UI', 11, 'bold'), padding=(16, 9))
        style.configure('Holmes.Treeview', rowheight=29, font=('Segoe UI', 11))
        self.banner = tk.StringVar(root, value='Local investigation • No observation running • No external services connected')
        bar = ttk.Frame(root, padding=(18, 12)); bar.pack(fill='x')
        ttk.Label(bar, text='Holmes Lab', style='Holmes.Title.TLabel').pack(side='left')
        ttk.Label(bar, textvariable=self.banner, wraplength=640).pack(side='right', padx=12)
        menu = tk.Menu(root)
        case_menu = tk.Menu(menu, tearoff=False)
        for label, fn in [('New case…', self.choose_new), ('Open case…', self.choose_journal),
                          ('Open evidence…', self.choose_capsule), ('Back up case…', self.choose_backup),
                          ('Export report…', self.choose_report), ('Close safely', self.close)]:
            case_menu.add_command(label=label, command=fn)
        menu.add_cascade(label='Case', menu=case_menu)
        tools_menu = tk.Menu(menu, tearoff=False)
        tools_menu.add_command(label='Microscope: observation and replay', command=self.open_microscope)
        tools_menu.add_command(label='Evidence library: capsules and comparison', command=self.open_library)
        menu.add_cascade(label='Advanced tools', menu=tools_menu)
        root.configure(menu=menu)
        root.bind('<Control-o>', lambda e: self.choose_journal())
        root.bind('<Control-n>', lambda e: self.choose_new())
        ttk.Label(root, textvariable=self.status, wraplength=1080, padding=(18, 6)).pack(side='bottom', fill='x')
        self.notebook = notebook = ttk.Notebook(root)
        notebook.pack(fill='both', expand=True, padx=18, pady=10)
        welcome = ttk.Frame(notebook, padding=22)
        evidence = ttk.Frame(notebook, padding=8)
        lab = ttk.Frame(notebook, padding=8)
        review = ttk.Frame(notebook, padding=12)
        history = ttk.Frame(notebook, padding=8)
        export = ttk.Frame(notebook, padding=22)
        advanced = ttk.Frame(notebook, padding=8)
        self.pages = dict(welcome=welcome, evidence=evidence, hypothesis=lab, review=review,
                          history=history, export=export, advanced=advanced)
        for frame, label in [(welcome, 'Start'), (evidence, '1  Evidence'), (lab, '2  Explanation'),
                             (review, '3  Challenge & review'), (history, 'History'), (export, 'Report'), (advanced, 'Advanced JSON')]:
            notebook.add(frame, text=label)
        self.heading(welcome, 'What happened — and how do we know?')
        ttk.Label(welcome, text='Build an investigation from selected evidence. Compare explanations, inspect their limits,\n'
                  'and preserve your assessment without changing the original observations.', wraplength=900).pack(anchor='w', pady=(8, 22))
        actions = ttk.Frame(welcome); actions.pack(anchor='w')
        self.demo_button = ttk.Button(actions, text='Try a synthetic demonstration', style='Holmes.Primary.TButton', command=self.start_demo)
        self.demo_button.pack(side='left', padx=(0, 12))
        ttk.Button(actions, text='Open an existing case…', command=self.choose_journal).pack(side='left')
        ttk.Button(actions, text='Create a case…', command=self.choose_new).pack(side='left', padx=12)
        self.heading(welcome, 'Your investigation, step by step', pady=(30, 8))
        ttk.Label(welcome, text='1. Select evidence: open a capsule and mark supporting or contrary records.\n\n'
                  '2. Build an explanation: state what it suggests and what remains unknown.\n\n'
                  '3. Challenge and review: examine limits, then record or correct your assessment.\n\n'
                  '4. Export a report: share selected findings and traceable citations.', wraplength=900).pack(anchor='w')
        self.heading(welcome, 'You remain in control', pady=(25, 8))
        ttk.Label(welcome, text='Opening this application starts no collection or external connection. Evidence is read-only.\n'
                  'A human assessment is an interpretation, never permission to execute a command.\n'
                  'The demonstration is generated locally and is clearly labeled SYNTHETIC.\n'
                  'Close the window to finish; completed journal revisions remain saved.', wraplength=900).pack(anchor='w')
        self.storage_label = ttk.Label(welcome, text=f'New case and demo location: {self.data_root}\nExisting cases stay where you selected them.', wraplength=900)
        self.storage_label.pack(anchor='w', pady=(20, 0))
        self.heading(lab, 'What does the evidence suggest?')
        form = ttk.Frame(lab); form.pack(fill='x')
        for row, (label, var) in enumerate([('Case title', self.title), ('Purpose', self.purpose), ('Declared reviewer', self.producer)]):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky='w')
            ttk.Entry(form, textvariable=var).grid(row=row, column=1, sticky='ew', padx=6, pady=2)
        form.columnconfigure(1, weight=1)
        self.hypotheses = ttk.Treeview(lab, columns=('claim', 'state', 'revision'), show='headings', height=3, style='Holmes.Treeview')
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
        self.reference_status = tk.StringVar(root, value='Supporting: 0 | Contradicting: 0')
        ttk.Label(lab, textvariable=self.reference_status).pack(anchor='w', pady=4)
        actions = ttk.Frame(lab); actions.pack(fill='x', pady=8)
        self.create_button = ttk.Button(actions, text='Save new explanation', command=self.propose, style='Holmes.Primary.TButton')
        self.create_button.pack(side='left')
        for label, fn in [('Revise selected', self.revise), ('New draft', self.new_hypothesis),
                          ('Clear draft references', self.clear_references), ('Next: challenge & review', lambda: self.navigate('review'))]:
            ttk.Button(actions, text=label, command=fn).pack(side='left', padx=5)
        self.heading(review, 'How strong is this explanation?')
        ttk.Label(review, text='Select a saved explanation on the previous page. A deterministic challenge checks citations and evidence gaps.\n'
                  'It cannot establish a unique cause or verify who produced the evidence.', wraplength=1000).pack(anchor='w', pady=8)
        challenge_bar = ttk.Frame(review); challenge_bar.pack(fill='x', pady=8)
        ttk.Button(challenge_bar, text='Challenge selected explanation', command=self.challenge, style='Holmes.Primary.TButton').pack(side='left')
        ttk.Button(challenge_bar, text='Find reviewed patterns', command=self.find_patterns).pack(side='left', padx=12)
        citebar = ttk.Frame(review); citebar.pack(fill='x', pady=8)
        self.citation_choice = ttk.Combobox(citebar, state='readonly', width=75)
        self.citation_choice.pack(side='left', fill='x', expand=True)
        ttk.Button(citebar, text='Inspect saved citation', command=self.resolve_citation).pack(side='left')
        self.summary = tk.Text(review, height=9, wrap='word'); self.summary.pack(fill='both', expand=True, pady=6)
        ttk.Label(review, text='Human assessment — choose a state and explain your reasoning.').pack(anchor='w', pady=(12, 4))
        review_row = ttk.Frame(review); review_row.pack(fill='x')
        ttk.Combobox(review_row, textvariable=self.review_state, values=STATES, state='readonly', width=30).pack(side='left')
        self.reason = ttk.Entry(review_row); self.reason.pack(side='left', fill='x', expand=True, padx=8)
        review_actions = ttk.Frame(review); review_actions.pack(fill='x', pady=10)
        ttk.Button(review_actions, text='Record assessment', command=lambda: self.review(False)).pack(side='left')
        ttk.Button(review_actions, text='Correct earlier assessment', command=lambda: self.review(True)).pack(side='left', padx=10)
        ttk.Label(review, text='Corrections add a revision. Earlier assessments remain inspectable. No action is authorized.').pack(anchor='w')
        self.heading(evidence, 'What happened? Select the records that matter.')
        ttk.Label(evidence, text='Capsules are read-only evidence packages. Classification is a source declaration; receipt order is not causal order.').pack(anchor='w', pady=8)
        evidence_bar = ttk.Frame(evidence); evidence_bar.pack(fill='x')
        ttk.Button(evidence_bar, text='Open evidence capsule…', command=self.choose_capsule).pack(side='left', padx=(0, 8))
        self.capsules = ttk.Combobox(evidence_bar, state='readonly', width=65)
        self.capsules.pack(fill='x', expand=True)
        self.capsules.bind('<<ComboboxSelected>>', self.select_capsule)
        self.evidence = ttk.Treeview(evidence, columns=('arrival', 'source', 'class', 'event', 'outcome'), show='headings', height=9, style='Holmes.Treeview')
        for col in ('arrival', 'source', 'class', 'event', 'outcome'):
            self.evidence.heading(col, text=col.title())
        self.evidence.pack(fill='both', expand=True, pady=6)
        self.evidence.bind('<<TreeviewSelect>>', self.select_evidence)
        buttons = ttk.Frame(evidence); buttons.pack(fill='x')
        for label, fn in [('Previous 100', self.previous_page), ('Next 100', self.next_page),
                          ('Use as support', lambda: self.attach('support')), ('Use as contradiction', lambda: self.attach('contradict'))]:
            ttk.Button(buttons, text=label, command=fn).pack(side='left', padx=4)
        ttk.Button(buttons, text='Next: build explanation', command=lambda: self.navigate('hypothesis')).pack(side='right')
        ttk.Label(evidence, textvariable=self.reference_status).pack(anchor='w', pady=6)
        self.evidence_summary = tk.Text(evidence, height=7, wrap='word'); self.evidence_summary.pack(fill='both', expand=True, pady=8)
        self.heading(history, 'What changed in our understanding?')
        self.history = ttk.Treeview(history, columns=('revision', 'kind', 'state', 'producer'), show='headings', style='Holmes.Treeview')
        for col in ('revision', 'kind', 'state', 'producer'):
            self.history.heading(col, text=col.title())
        self.history.pack(fill='both', expand=True)
        self.history.bind('<<TreeviewSelect>>', self.select_revision)
        nav = ttk.Frame(history); nav.pack(fill='x')
        ttk.Button(nav, text='Previous 100 revisions', command=self.previous_history).pack(side='left')
        ttk.Button(nav, text='Next 100 revisions', command=self.next_history).pack(side='left')
        self.history_summary = tk.Text(history, height=10, wrap='word'); self.history_summary.pack(fill='both', expand=True)
        self.heading(export, 'Share findings with their limits')
        ttk.Label(export, text='Export the selected case as a self-contained HTML report or structured JSON.\n'
                  'The report includes interpretations, assessment history and only cited evidence metadata.\n'
                  'It does not embed entire sessions or confer forensic certification.\n\n'
                  'Your written interpretations may contain sensitive information: review the report before sharing.\n'
                  'Choose a new destination; existing reports are never overwritten.', wraplength=950).pack(anchor='w', pady=20)
        ttk.Button(export, text='Export investigation report…', command=self.choose_report, style='Holmes.Primary.TButton').pack(anchor='w')
        ttk.Button(export, text='Create a verified journal backup…', command=self.choose_backup).pack(anchor='w', pady=18)
        self.raw = tk.Text(advanced, wrap='word'); self.raw.pack(fill='both', expand=True)
        for widget in (self.claim, self.uncertainty, self.alternatives, self.missing, self.checks,
                       self.summary, self.evidence_summary, self.history_summary, self.raw):
            widget.bind('<Tab>', lambda e: self.focus_next(e.widget))
            widget.bind('<Shift-Tab>', lambda e: self.focus_next(e.widget, backwards=True))
        self.put(self.summary, 'Save an explanation, then run a challenge. Findings and limitations will appear here.')
        self.put(self.evidence_summary, 'Open a capsule or try the synthetic demonstration on Start. Select a record to read its summary.')
        self.put(self.history_summary, 'Every saved interpretation and correction remains in the history. Select a revision to inspect it.')
        self.put(self.raw, 'Advanced structured data appears here after you select evidence or an interpretation.')
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.timer = root.after(30, self.poll)

    @staticmethod
    def heading(parent, value, pady=(0, 8)):
        ttk.Label(parent, text=value, style='Holmes.Heading.TLabel').pack(anchor='w', pady=pady)

    @staticmethod
    def focus_next(widget, backwards=False):
        (widget.tk_focusPrev() if backwards else widget.tk_focusNext()).focus_set()
        return 'break'

    def navigate(self, page):
        self.notebook.select(self.pages[page])

    def open_microscope(self):
        # Independent Tk root isolates the legacy microscope's global theme settings.
        from apm.ui.main_window import APMWindow
        child = tk.Tk()
        child.apm = APMWindow(child, sessions_root=self.data_root / 'sessions')
        self.microscopes.append(child.apm)
        self.banner.set('Advanced microscope opened • Observation controls are in that window • No model providers')

    def open_library(self):
        if self.busy: return
        from apm.evidence.capsule import Capsule
        from apm.ui.capsule_window import CapsuleWindow
        path = filedialog.askopenfilename(parent=self.root, title='Open read-only evidence library', filetypes=[('Evidence capsule', '*.apmcapsule')])
        if not path: return
        def done(capsule):
            child = tk.Toplevel(self.root)
            child.apm = CapsuleWindow(child, capsule)
        self.submit(lambda: Capsule.open(path), done)

    def select_capsule(self, event=None):
        index = self.capsules.current()
        if index >= 0:
            self.capsule_sha.set(self.catalog.summaries()[index]['sha256'])
            self.load_page(reset=True)

    def refresh_capsules(self, sha):
        summaries = self.catalog.summaries()
        self.capsules.configure(values=[f"Evidence package {n + 1} — {s['records']} records" for n, s in enumerate(summaries)])
        self.capsules.current(next(n for n, s in enumerate(summaries) if s['sha256'] == sha))
        self.capsule_sha.set(sha)

    def start_demo(self):
        if self.busy: return
        if self.path is not None:
            self.status.set('Open another APM window for a new demonstration; your current case stays selected.'); return
        from apm.desktop_demo import create_demo
        destination = self.data_root / 'demonstrations' / str(uuid4())
        def work():
            result = create_demo(destination)
            catalog = Catalog()
            shas = [catalog.open(path) for path in result['capsules']]
            return result, catalog, shas
        def done(value):
            result, self.catalog, shas = value
            self.path, self.case_id = result['journal'], result['case_id']
            self.title.set('SYNTHETIC demonstration: conflicting test outcomes')
            self.purpose.set('Practice investigation; these records describe no real agent or command.')
            self.banner.set('SYNTHETIC DEMONSTRATION • No real observation • No external services')
            self.new_hypothesis()
            self.refresh([])
            self.refresh_capsules(shas[0])
            self.load_page(reset=True)
            self.navigate('evidence')
        self.submit(work, done)

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
        if self.busy or self.closed or self.closing:
            self.status.set('Please wait for the current bounded operation to finish.'); return
        self.busy = True; self.status.set('Working locally…')
        self.callback = callback
        self.future = self.executor.submit(operation)

    def poll(self):
        if self.closed:
            return
        if self.future is not None and self.future.done():
            future, self.future = self.future, None
            callback, self.callback = self.callback, None
            self.busy = False
            try:
                result = future.result()
                self.status.set('Ready. Source evidence unchanged; no execution authority.')
                if not self.closing: callback(result)
            except Exception as exc:
                # Do not display exception text potentially containing a private path or input.
                if isinstance(exc, FileExistsError):
                    self.status.set('Choose a new destination. The existing file was preserved.')
                elif isinstance(exc, PermissionError):
                    self.status.set('This location is not accessible. Choose a folder you can write to; existing evidence was preserved.')
                else:
                    self.status.set('Operation rejected or unavailable. Check citations, field limits, review selection and destination. Sources unchanged.')
        self.timer = self.root.after(30, self.poll)

    def choose_new(self):
        if self.busy: return
        directory = self.data_root / 'cases'
        try: directory.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.status.set('The default case location is unavailable. Use Open case to select an existing accessible case.'); return
        path = filedialog.asksaveasfilename(parent=self.root, title='Create a new APM case',
            initialdir=directory, initialfile='investigation.sqlite3', defaultextension='.sqlite3', filetypes=[('APM case', '*.sqlite3')])
        if path: self.open_journal(path, create=True)

    def choose_journal(self):
        path = filedialog.askopenfilename(parent=self.root, title='Open an APM investigation case', filetypes=[('APM case', '*.sqlite3')])
        if path: self.open_journal(path)

    def open_journal(self, path, create=False):
        path = Path(path)
        def work():
            with (Journal.create(path) if create else Journal(path)) as journal:
                return journal.all_entries(), journal.verify()
        def done(result):
            self.path = path; self.new_hypothesis(); self.case_id = str(uuid4())
            self.refresh(result[0])
            if result[0]:
                self.hypotheses.selection_set(result[0][-1]['hypothesis_id']); self.select_hypothesis()
            else:
                self.title.set('New investigation')
                self.purpose.set('Understand the evidence and what remains unknown.')
            self.banner.set('Local case • Source identity unverified • Reviews authorize no actions')
            self.status.set(f"Case opened: {result[1]['entries']} saved revisions. Journal integrity checks passed; details on Advanced JSON.")
            self.put(self.raw, json.dumps(dict(journal_integrity=result[1]), indent=2))
            self.navigate('hypothesis' if result[0] else 'evidence')
        self.submit(work, done)

    def choose_capsule(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[('Evidence capsule', '*.apmcapsule')])
        if path: self.open_capsule(path)

    def open_capsule(self, path):
        def done(sha):
            self.refresh_capsules(sha); self.load_page(reset=True); self.navigate('evidence')
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
            total = next(s['records'] for s in self.catalog.summaries() if s['sha256'] == sha)
            self.status.set(f"Page {len(self.page_stack) + 1}: {len(page)} records shown, {total} in this package. Internal hashes checked; source identity unverified.")
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
        self.status.set('Added to the draft explanation. Save the explanation to preserve these references.')

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
        self.put(self.summary, 'Write an explanation, its uncertainty and alternatives. Select evidence on Evidence, then save the explanation.')

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
        self.citation_choice.configure(values=[f"{role.title()} — evidence {n + 1}"
                                              for role in ('support', 'contradict') for n, r in enumerate(h[role])])
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
        if self.closed: return
        self.closing = True
        if self.future is not None and not self.future.done():
            self.status.set('Finishing the current local operation before closing. Source evidence remains unchanged.')
            self.root.after(50, self.close)
            return
        self.closed = True
        self.callback = None
        for microscope in self.microscopes:
            try:
                if microscope.root.winfo_exists(): microscope.close()
            except tk.TclError:
                pass
        self.root.after_cancel(self.timer)
        self.executor.shutdown(wait=True, cancel_futures=True)
        self.root.destroy()


def run_desktop(data_root=None):
    root = tk.Tk()
    HolmesWindow(root, data_root=data_root)
    root.mainloop()
    return 0
