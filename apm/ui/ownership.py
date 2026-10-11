"""Tk belongs to the main thread; worker outcomes contain no tracebacks.

Only data operations may be submitted. Callbacks remain on the GUI owner.
In particular, never re-raise a Future's stored exception in a Tk frame:
its traceback would retain that frame, its window and the same Future.
"""
from dataclasses import dataclass
from functools import wraps
import inspect
import threading


def require_gui_thread():
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError('APM GUI operations require the main GUI thread')


def owner_thread_only(cls):
    """Guard GUI methods before touching Tk; workers are module-level functions."""
    for name, method in list(vars(cls).items()):
        is_static = isinstance(method, staticmethod)
        if is_static:
            method = method.__func__
        if inspect.isfunction(method):
            @wraps(method)
            def guarded(*args, __method=method, **kwargs):
                require_gui_thread()
                return __method(*args, **kwargs)
            setattr(cls, name, staticmethod(guarded) if is_static else guarded)
    return cls


@dataclass(frozen=True)
class Outcome:
    value: object = None
    error: str | None = None


def run_operation(operation):
    """Return data or a diagnostic class name, never an exception/traceback."""
    try:
        return Outcome(value=operation())
    except Exception as error:
        return Outcome(error=type(error).__name__)
