"""Offline capsule commands; import means an isolated read-only context."""
import json
import sqlite3
from pathlib import Path

from .capsule import Capsule, export_session
from .compare import compare


def add_commands(commands):
    capsule = commands.add_parser('capsule', help='Offline redacted evidence exchange; no execution or database import')
    actions = capsule.add_subparsers(dest='capsule_operation', required=True)
    export = actions.add_parser('export', help='Disclose one selected session to a NEW local capsule')
    export.add_argument('database', type=Path)
    export.add_argument('--session', required=True)
    export.add_argument('--case', required=True, help='Owner-selected case UUID')
    export.add_argument('--output', required=True, type=Path)
    export.add_argument('--include-human', action='store_true', help='Explicitly include human opinion records; never execution grants')
    export.add_argument('--include-text', action='store_true', help='Disclose sanitized free text; review for personal/confidential information before sharing')
    export.add_argument('--expected-tip')
    for name in ('verify', 'inspect', 'gui'):
        command = actions.add_parser(name)
        command.add_argument('path', type=Path)
        command.add_argument('--expected-sha256', help='Independently retained file digest; not a signer identity')
        if name == 'inspect':
            command.add_argument('--after', type=int, default=0)
            command.add_argument('--evidence-id', help='Resolve one retained citation instead of a page')
    comparison = actions.add_parser('compare', help='Compare two distinct session capsules without executing checks')
    comparison.add_argument('left', type=Path)
    comparison.add_argument('right', type=Path)


def run_command(args):
    if args.command != 'capsule':
        return None
    try:
        return _run(args)
    except sqlite3.Error:
        raise ValueError('capsule_source_database_unavailable') from None


def _run(args):
    if args.capsule_operation == 'export':
        value = export_session(args.database, args.session, args.case, args.output,
            include_human=args.include_human, include_text=args.include_text, expected_tip=args.expected_tip)
    elif args.capsule_operation == 'compare':
        value = compare(Capsule.open(args.left), Capsule.open(args.right))
    else:
        capsule = Capsule.open(args.path, expected_sha256=args.expected_sha256)
        if args.capsule_operation == 'gui':
            import tkinter as tk
            from apm.ui.capsule_window import CapsuleWindow
            root = tk.Tk(); CapsuleWindow(root, capsule); root.mainloop()
            return 0
        if args.capsule_operation == 'inspect':
            value = capsule.resolve(args.evidence_id) if args.evidence_id else capsule.page(after=args.after)
        else:
            value = capsule.summary()
    print(json.dumps(value, indent=2))
    return 0
