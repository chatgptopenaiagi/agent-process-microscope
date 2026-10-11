"""Explicit local Holmes entry points; no execution or provider commands."""
import json
from pathlib import Path
import sqlite3


def add_commands(commands):
    command = commands.add_parser('holmes', help='Local hypotheses and human review; no execution authority')
    sub = command.add_subparsers(dest='holmes_operation', required=True)
    gui = sub.add_parser('gui'); gui.add_argument('journal', type=Path, nargs='?')
    verify = sub.add_parser('verify'); verify.add_argument('journal', type=Path); verify.add_argument('--expected-tip')
    patterns = sub.add_parser('patterns'); patterns.add_argument('journal', type=Path)
    patterns.add_argument('--capsule', type=Path, action='append', default=[])
    report = sub.add_parser('report'); report.add_argument('journal', type=Path)
    report.add_argument('--case', required=True); report.add_argument('--capsule', type=Path, action='append', default=[])
    report.add_argument('--output', type=Path, required=True)


def run_command(args):
    if args.command != 'holmes': return None
    from .journal import Journal
    from .model import Catalog
    from .report import export_report
    try:
        if args.holmes_operation == 'gui':
            import tkinter as tk
            from apm.ui.holmes_window import HolmesWindow
            root = tk.Tk(); window = HolmesWindow(root)
            if args.journal: window.open_journal(args.journal)
            root.mainloop(); return 0
        with Journal(args.journal) as journal:
            if args.holmes_operation == 'verify': result = journal.verify(args.expected_tip)
            else:
                catalog = Catalog()
                for path in args.capsule: catalog.open(path)
                if args.holmes_operation == 'patterns':
                    from .patterns import retrieve
                    result = retrieve(journal, catalog)
                else: result = export_report(journal, catalog, args.case, args.output)
        print(json.dumps(result, indent=2)); return 0
    except sqlite3.Error as exc:
        raise ValueError('holmes_database_unavailable_or_invalid') from exc
