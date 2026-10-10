"""Desktop data locations; resolving a location does not create or scan it."""
import os
from pathlib import Path
import sys


def user_data_root(override=None):
    if override is not None:
        return Path(override).expanduser().resolve()
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local')
    else:
        base = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share')
    return base / 'APM'


def sessions_root():
    """Retain source-checkout behavior; installed apps use a writable user location."""
    source = Path(__file__).resolve().parent.parent
    if not getattr(sys, 'frozen', False) and (source / 'pyproject.toml').is_file():
        return source / 'sessions'
    return user_data_root() / 'sessions'
