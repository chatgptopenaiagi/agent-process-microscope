"""Disposable, SYNTHETIC-ONLY fixtures inside the authorized repository.

Inherit the project directory permissions; do not request Windows' private 0700
ACL, patch tempfile/os.mkdir, or alter an existing ACL. Never use for credentials
or owner evidence. Production storage and temporary-file policy are unchanged.
"""
from pathlib import Path
import os
import stat
import shutil
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


class SyntheticDirectory:
    def __init__(self, prefix='synthetic-', dir=None):
        parent = Path(dir).resolve() if dir else ROOT / 'cache' / 'test-fixtures'
        if not parent.is_relative_to(ROOT) or parent.is_symlink():
            raise ValueError('Synthetic fixtures must remain project-local')
        if any(c in prefix for c in '/\\:') or len(prefix) > 60:
            raise ValueError('Invalid fixture prefix')
        parent.mkdir(parents=True, exist_ok=True)
        self.path = parent / (prefix + str(uuid4()))
        self.path.mkdir()  # Inherited permissions, not a global security change.
        self.name = str(self.path)
        self.marker = parent / (self.path.name + '.apm-synthetic-fixture')
        self.marker.write_text('SYNTHETIC ONLY', encoding='ascii')

    def __enter__(self):
        return self.name

    def __exit__(self, *args):
        self.cleanup()

    def cleanup(self):
        if not self.path.exists():
            return
        if (not self.path.resolve().is_relative_to(ROOT) or self.path.is_symlink()
                or self.path.is_junction() or not self.marker.is_file()):
            raise ValueError('Refusing cleanup of an unowned fixture')
        def readonly_file(function, name, error):
            target = Path(name)
            # Git creates read-only object files. Clear only the DOS read-only
            # attribute on files owned by this fixture; never repair an ACL.
            if (os.name == 'nt' and function is os.unlink and target.is_file()
                    and not target.is_symlink() and target.resolve().is_relative_to(self.path)
                    and target.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY):
                target.chmod(stat.S_IWRITE)
                function(name)
            else:
                raise error
        shutil.rmtree(self.path, onexc=readonly_file)
        self.marker.unlink()
