"""Run with .venv/Scripts/pythonw.exe; no PowerShell or console helper."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))
try:
    from apm.ui.main_window import run_gui
    run_gui(workspace=root, sessions_root=root / 'sessions')
except Exception as exc:
    from apm.security.redaction import redact_text
    from tkinter import messagebox
    report = root / 'reports' / 'launch-error.txt'
    report.parent.mkdir(exist_ok=True)
    report.write_text(redact_text(f'{type(exc).__name__}: {exc}'), encoding='utf-8')
    messagebox.showerror('APM could not start', f'See {report}')
