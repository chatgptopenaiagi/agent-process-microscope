"""Run with .venv/Scripts/pythonw.exe; no PowerShell or console helper."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))
try:
    from apm.ui.holmes_window import run_desktop
    run_desktop()
except Exception as exc:
    from apm.security.redaction import redact_text
    from tkinter import messagebox
    from apm.paths import user_data_root
    from uuid import uuid4
    report = user_data_root() / 'reports' / ('launch-error-' + str(uuid4()) + '.txt')
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(redact_text(f'{type(exc).__name__}: {exc}'), encoding='utf-8')
    messagebox.showerror('APM could not start', f'See {report}')
