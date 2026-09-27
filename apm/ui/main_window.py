"""APM native Tk interface. Observation starts only from an explicit action."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, ttk
from types import SimpleNamespace

from .model import (LENSES, TimelineBuffer, bytes_text, clock_text, duration_text,
                    event_dict, event_lens, matches, timestamp)

PALETTE = {"bg": "#09121e", "panel": "#101e2e", "raised": "#16283c",
           "border": "#293e54", "text": "#e5eef7", "muted": "#9ab0c4",
           "teal": "#61dfc6", "amber": "#f4c57b", "selection": "#24526a",
           "red": "#f18e92"}
MODES = ("Attach process", "Synthetic demo")


def controller_factory(**kwargs):
    from apm.core.controller import Controller
    return Controller(**kwargs)


def session_reader(path):
    from apm.storage.reader import read_session
    return read_session(path)


def replay_state_engine():
    from apm.core.state import StateEngine
    return StateEngine()


class APMWindow:
    """UI-owned lifecycle and bounded view; all adapter work stays in Controller."""

    def __init__(self, root, workspace=None, sessions_root=None, pid=None, demo=False,
                 controller_factory=controller_factory, session_reader=session_reader):
        self.root = root
        self._factory, self._reader = controller_factory, session_reader
        self.buffer = TimelineBuffer()
        self.controller = None
        self._active = self._starting = self._stopping = self._loading = False
        self._closing = False
        self._messages = queue.Queue(maxsize=8)
        self._timer = self._filter_timer = None
        self._pending_session = None
        self._selected = None
        self._display_events = {}
        self._paused_new = 0
        self._received = 0
        self._state_time = None
        self._replay_mode = self._replay_playing = False
        self._replay_events = []
        self._replay_index = 0
        self._replay_anchor = self._replay_elapsed = 0.0
        self._replay_clock = None
        self._replay_info = {}
        self._replay_engine = None
        self._session_started = None
        self._session_ended = None
        self._session_path = None
        self._last_metadata = {}
        self.workspace_var = tk.StringVar(root, str(workspace or Path.cwd()))
        default_sessions = Path(__file__).resolve().parents[2] / "sessions"
        self.sessions_var = tk.StringVar(root, str(sessions_root or default_sessions))
        self.pid_var = tk.StringVar(root, "" if pid is None else str(pid))
        self.mode_var = tk.StringVar(root, "Synthetic demo" if demo else "Attach process")
        self.category_var = tk.StringVar(root, "All categories")
        self.status_var = tk.StringVar(root, "All statuses")
        self.search_var = tk.StringVar(root)
        self.paused_var = tk.BooleanVar(root, False)
        self.lens_var = tk.StringVar(root, LENSES[0])
        self.speed_var = tk.StringVar(root, "1×")
        self.header_var = tk.StringVar(root, "READY TO OBSERVE")
        self.header_detail_var = tk.StringVar(root, "No observation is running")
        self.activity_var = tk.StringVar(root, "Waiting for your start")
        self.activity_detail_var = tk.StringVar(root, "Select a workspace or process. Activity will appear here after you start.")
        self.duration_var = tk.StringVar(root, "—")
        self.count_var = tk.StringVar(root, "0 visible · 0 buffered")
        self.footer_var = tk.StringVar(root, "Local only. Stopping observation never stops the attached process.")
        self.session_vars = {name: tk.StringVar(root, "—") for name in
                             ("Session", "Scope", "Process", "Received", "Dropped", "Elapsed", "Location")}
        self.telemetry_vars = {name: tk.StringVar(root, "Awaiting sample") for name in ("CPU", "RAM", "DISK I/O", "NETWORK", "GPU")}
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Control-f>", self._focus_search)
        self.root.bind("<Control-o>", lambda _event: self.choose_session())
        for variable in (self.category_var, self.status_var, self.search_var):
            variable.trace_add("write", self._schedule_filter)
        self.mode_var.trace_add("write", lambda *_: self._sync_controls())
        self.speed_var.trace_add("write", lambda *_: self._speed_changed())
        self._sync_controls()
        self._timer = self.root.after(150, self._tick)

    def _build(self):
        p = PALETTE
        self.root.title("APM — Agent Process Microscope")
        self.root.geometry("1400x900")
        self.root.minsize(1060, 720)
        self.root.configure(background=p["bg"])
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background=p["bg"], foreground=p["text"])
        style.configure("TFrame", background=p["bg"])
        style.configure("Card.TFrame", background=p["panel"])
        style.configure("TLabel", background=p["bg"], foreground=p["text"])
        style.configure("Muted.TLabel", foreground=p["muted"])
        style.configure("Card.TLabel", background=p["panel"])
        style.configure("CardMuted.TLabel", background=p["panel"], foreground=p["muted"])
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 24))
        style.configure("Section.TLabel", font=("Segoe UI Semibold", 11))
        style.configure("TButton", padding=(12, 7), background=p["raised"], bordercolor=p["border"], lightcolor=p["raised"], darkcolor=p["raised"])
        style.map("TButton", background=[("active", "#243e55"), ("disabled", p["panel"])], foreground=[("disabled", "#637b91")])
        style.configure("Accent.TButton", foreground=p["bg"], background=p["teal"], font=("Segoe UI Semibold", 10))
        style.map("Accent.TButton", background=[("active", "#8eead7"), ("disabled", p["raised"])], foreground=[("disabled", "#71899d")])
        style.configure("TEntry", fieldbackground=p["panel"], foreground=p["text"], bordercolor=p["border"], padding=7, insertcolor=p["text"])
        style.configure("TCombobox", fieldbackground=p["panel"], background=p["raised"], foreground=p["text"], arrowcolor=p["muted"], padding=6)
        style.map("TCombobox", fieldbackground=[("readonly", p["panel"])], foreground=[("readonly", p["text"]), ("disabled", "#71899d")])
        self.root.option_add("*TCombobox*Listbox.background", p["panel"])
        self.root.option_add("*TCombobox*Listbox.foreground", p["text"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", p["selection"])
        style.configure("TCheckbutton", background=p["bg"], foreground=p["text"], padding=5)
        style.map("TCheckbutton", background=[("active", p["bg"])])
        style.configure("Lens.TRadiobutton", background=p["raised"], padding=(8, 7))
        style.map("Lens.TRadiobutton", background=[("selected", p["selection"]), ("active", "#243e55")], foreground=[("selected", p["teal"])])
        style.configure("Treeview", background=p["panel"], fieldbackground=p["panel"], foreground=p["text"], rowheight=29, borderwidth=0)
        style.configure("Treeview.Heading", background=p["raised"], foreground=p["muted"], relief="flat", padding=7, font=("Segoe UI Semibold", 9))
        style.map("Treeview", background=[("selected", p["selection"])], foreground=[("selected", "#ffffff")])
        style.map("Treeview.Heading", background=[("active", "#243e55")])
        style.configure("Vertical.TScrollbar", background=p["raised"], troughcolor=p["panel"], arrowcolor=p["muted"], borderwidth=0)
        style.configure("TPanedwindow", background=p["bg"])
        outer = ttk.Frame(self.root, padding=(24, 20, 24, 12))
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x")
        title = ttk.Frame(header)
        title.pack(side="left")
        ttk.Label(title, text="APM", foreground=p["teal"], font=("Segoe UI Semibold", 11)).pack(anchor="w")
        ttk.Label(title, text="Agent Process Microscope", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title, text="External actions. Traceable evidence. Clear boundaries.", style="Muted.TLabel").pack(anchor="w", pady=(2, 0))
        status = ttk.Frame(header)
        status.pack(side="right", anchor="n", pady=8)
        self.header_label = ttk.Label(status, textvariable=self.header_var, foreground=p["teal"], font=("Segoe UI Semibold", 12))
        self.header_label.pack(anchor="e")
        ttk.Label(status, textvariable=self.header_detail_var, style="Muted.TLabel").pack(anchor="e", pady=(5, 0))
        config = ttk.Frame(outer)
        config.pack(fill="x", pady=(21, 6))
        config.columnconfigure(1, weight=3)
        config.columnconfigure(5, weight=2)
        for column, label in ((0, "MODE"), (1, "WORKSPACE"), (3, "ROOT PID"), (5, "SESSIONS DIRECTORY")):
            ttk.Label(config, text=label, style="Muted.TLabel", font=("Segoe UI Semibold", 9)).grid(row=0, column=column, sticky="w", pady=(0, 5))
        self.mode_box = ttk.Combobox(config, textvariable=self.mode_var, values=MODES, state="readonly", width=19)
        self.mode_box.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.workspace_entry = ttk.Entry(config, textvariable=self.workspace_var)
        self.workspace_entry.grid(row=1, column=1, sticky="ew")
        self.workspace_button = ttk.Button(config, text="…", width=2, command=lambda: self._choose_directory(self.workspace_var, "Select workspace"))
        self.workspace_button.grid(row=1, column=2, padx=(4, 10))
        self.pid_entry = ttk.Entry(config, textvariable=self.pid_var, width=9)
        self.pid_entry.grid(row=1, column=3, padx=(0, 14))
        self.sessions_entry = ttk.Entry(config, textvariable=self.sessions_var)
        self.sessions_entry.grid(row=1, column=5, sticky="ew")
        self.sessions_button = ttk.Button(config, text="…", width=2, command=lambda: self._choose_directory(self.sessions_var, "Select sessions directory"))
        self.sessions_button.grid(row=1, column=6, padx=(4, 0))
        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(6, 16))
        self.start_button = ttk.Button(actions, text="Start observation", style="Accent.TButton", command=self.start_observation)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(actions, text="Stop observation", command=self.stop_observation)
        self.stop_button.pack(side="left", padx=6)
        ttk.Checkbutton(actions, text="Pause display", variable=self.paused_var, command=self.toggle_pause).pack(side="left", padx=(10, 4))
        ttk.Button(actions, text="Clear view", command=self.clear_view).pack(side="left", padx=4)
        self.open_button = ttk.Button(actions, text="Open session…", command=self.choose_session)
        self.open_button.pack(side="left", padx=4)
        self.replay_controls = ttk.Frame(actions)
        self.replay_controls.pack(side="right")
        self.leave_button = ttk.Button(self.replay_controls, text="Leave replay", command=self.leave_replay)
        self.leave_button.pack(side="right", padx=(8, 0))
        self.speed_box = ttk.Combobox(self.replay_controls, textvariable=self.speed_var, values=("1×", "4×", "Instant"), width=7, state="readonly")
        self.speed_box.pack(side="right", padx=4)
        self.replay_stop_button = ttk.Button(self.replay_controls, text="Reset replay", command=self.stop_replay)
        self.replay_stop_button.pack(side="right", padx=4)
        self.replay_button = ttk.Button(self.replay_controls, text="Play replay", command=self.toggle_replay)
        self.replay_button.pack(side="right", padx=4)
        overview = ttk.Frame(outer)
        overview.pack(fill="x", pady=(0, 15))
        overview.columnconfigure(0, weight=2)
        overview.columnconfigure(1, weight=3)
        activity = ttk.Frame(overview, style="Card.TFrame", padding=15)
        activity.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ttk.Label(activity, text="CURRENT ACTIVITY", style="CardMuted.TLabel", font=("Segoe UI Semibold", 9)).pack(anchor="w")
        row = ttk.Frame(activity, style="Card.TFrame")
        row.pack(fill="x", pady=(7, 4))
        ttk.Label(row, textvariable=self.activity_var, style="Card.TLabel", font=("Segoe UI Semibold", 16)).pack(side="left")
        ttk.Label(row, textvariable=self.duration_var, style="CardMuted.TLabel", font=("Consolas", 12)).pack(side="right")
        ttk.Label(activity, textvariable=self.activity_detail_var, style="CardMuted.TLabel", wraplength=460).pack(anchor="w", fill="x")
        telemetry = ttk.Frame(overview, style="Card.TFrame", padding=15)
        telemetry.grid(row=0, column=1, sticky="nsew")
        ttk.Label(telemetry, text="SYSTEM TELEMETRY  ·  AGGREGATE, NOT AGENT ATTRIBUTION", style="CardMuted.TLabel", font=("Segoe UI Semibold", 9)).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 10))
        for column, name in enumerate(self.telemetry_vars):
            telemetry.columnconfigure(column, weight=1)
            ttk.Label(telemetry, text=name, style="CardMuted.TLabel", font=("Segoe UI Semibold", 9)).grid(row=1, column=column, sticky="w", padx=(0, 12))
            ttk.Label(telemetry, textvariable=self.telemetry_vars[name], style="Card.TLabel", wraplength=125, font=("Segoe UI", 10)).grid(row=2, column=column, sticky="nw", padx=(0, 12), pady=(5, 0))
        split = ttk.Panedwindow(outer, orient="horizontal")
        split.pack(fill="both", expand=True)
        left = ttk.Frame(split)
        right = ttk.Frame(split, padding=(16, 0, 0, 0))
        split.add(left, weight=3)
        split.add(right, weight=2)
        timeline_title = ttk.Frame(left)
        timeline_title.pack(fill="x", pady=(0, 8))
        ttk.Label(timeline_title, text="Activity timeline", style="Section.TLabel").pack(side="left")
        ttk.Label(timeline_title, textvariable=self.count_var, style="Muted.TLabel", font=("Segoe UI", 9)).pack(side="right")
        filters = ttk.Frame(left)
        filters.pack(fill="x", pady=(0, 8))
        self.category_box = ttk.Combobox(filters, textvariable=self.category_var, values=("All categories",), state="readonly", width=15)
        self.category_box.pack(side="left", padx=(0, 6))
        ttk.Combobox(filters, textvariable=self.status_var, values=("All statuses", "observed", "inferred", "synthetic", "unavailable", "unknown"), state="readonly", width=13).pack(side="left", padx=(0, 6))
        self.search_entry = ttk.Entry(filters, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True)
        ttk.Label(filters, text="Search  Ctrl+F", style="Muted.TLabel", font=("Segoe UI", 9)).pack(side="right", padx=(6, 0))
        tree_frame = ttk.Frame(left)
        tree_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_frame, columns=("time", "category", "action", "target", "status"), show="headings", selectmode="browse")
        widths = (100, 85, 140, 230, 82)
        for name, width, title_text in zip(self.tree["columns"], widths, ("TIME · LOCAL", "CATEGORY", "ACTION", "TARGET", "STATUS")):
            self.tree.heading(name, text=title_text)
            self.tree.column(name, width=width, minwidth=65, stretch=name == "target")
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.tag_configure("inferred", foreground=p["teal"])
        self.tree.tag_configure("synthetic", foreground=p["amber"])
        self.tree.tag_configure("unavailable", foreground=p["amber"])
        self.tree.tag_configure("unknown", foreground=p["muted"])
        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)
        ttk.Label(left, text="Latest 2,000 events in view. Filters and Clear view never delete session evidence.", style="Muted.TLabel", font=("Segoe UI", 9)).pack(anchor="w", pady=(7, 0))
        ttk.Label(right, text="Evidence magnification", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        lenses = ttk.Frame(right)
        lenses.pack(fill="x", pady=(0, 8))
        for number, lens in enumerate(LENSES, 1):
            ttk.Radiobutton(lenses, text=f"{number}  {lens}", value=lens, variable=self.lens_var, command=self._show_details, style="Lens.TRadiobutton").pack(side="left", padx=(0, 4))
        detail_frame = ttk.Frame(right)
        detail_frame.pack(fill="both", expand=True)
        self.details = tk.Text(detail_frame, background=p["panel"], foreground=p["text"], insertbackground=p["text"], relief="flat", borderwidth=0, wrap="word", padx=14, pady=14, font=("Consolas", 10), width=42, height=12, state="disabled", selectbackground=p["selection"])
        detail_scroll = ttk.Scrollbar(detail_frame, orient="vertical", command=self.details.yview)
        self.details.configure(yscrollcommand=detail_scroll.set)
        self.details.pack(side="left", fill="both", expand=True)
        detail_scroll.pack(side="right", fill="y")
        session = ttk.Frame(right, style="Card.TFrame", padding=12)
        session.pack(fill="x", pady=(12, 0))
        session.columnconfigure(1, weight=1)
        ttk.Label(session, text="SESSION INFORMATION", style="CardMuted.TLabel", font=("Segoe UI Semibold", 9)).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        for row_index, (name, variable) in enumerate(self.session_vars.items(), 1):
            ttk.Label(session, text=name, style="CardMuted.TLabel", width=11, font=("Segoe UI", 9)).grid(row=row_index, column=0, sticky="nw", pady=1)
            ttk.Label(session, textvariable=variable, style="Card.TLabel", wraplength=405, font=("Segoe UI", 9)).grid(row=row_index, column=1, sticky="w", pady=1)
        ttk.Label(outer, textvariable=self.footer_var, style="Muted.TLabel", font=("Segoe UI", 9), wraplength=1250).pack(fill="x", pady=(12, 0))
        self._show_details()

    def _focus_search(self, _event=None):
        self.search_entry.focus_set()
        return "break"

    def _choose_directory(self, variable, title):
        result = filedialog.askdirectory(parent=self.root, title=title, initialdir=variable.get() or str(Path.cwd()))
        if result:
            variable.set(result)

    def _sync_controls(self):
        busy = self._active or self._starting or self._stopping or self._loading
        configurable = not busy and not self._replay_mode
        self.mode_box.configure(state="readonly" if configurable else "disabled")
        for widget in (self.workspace_entry, self.workspace_button, self.sessions_entry, self.sessions_button):
            widget.configure(state="normal" if configurable else "disabled")
        self.pid_entry.configure(state="normal" if configurable and self.mode_var.get() == "Attach process" else "disabled")
        self.start_button.configure(state="normal" if configurable and not self._closing else "disabled")
        self.stop_button.configure(state="normal" if self._active and not self._stopping else "disabled")
        self.open_button.configure(state="disabled" if self._starting or self._stopping or self._loading else "normal")
        for widget in (self.replay_button, self.replay_stop_button, self.leave_button):
            widget.configure(state="normal" if self._replay_mode and not self._loading else "disabled")
        self.speed_box.configure(state="readonly" if self._replay_mode else "disabled")
        self.replay_button.configure(text="Pause replay" if self._replay_playing else "Play replay")

    def _error(self, message, error=None):
        self.footer_var.set(message + (f" ({type(error).__name__}; no private error payload displayed)" if error else ""))

    def start_observation(self):
        if self._active or self._starting or self._stopping or self._replay_mode or self._loading:
            return
        workspace = Path(self.workspace_var.get()).expanduser()
        if not workspace.is_dir():
            self._error("Choose an existing workspace directory.")
            return
        pid = None
        if self.mode_var.get() == "Attach process":
            try:
                pid = int(self.pid_var.get())
                if pid <= 0:
                    raise ValueError()
            except ValueError:
                self._error("Enter a positive root process ID. APM will observe it without controlling it.")
                return
        if not self.sessions_var.get().strip():
            self._error("Choose a sessions directory.")
            return
        settings = dict(workspace=workspace.resolve(), sessions_root=Path(self.sessions_var.get()).expanduser().resolve(),
                        pid=pid, demo=self.mode_var.get() == "Synthetic demo")
        self._starting = True
        self.header_var.set("STARTING OBSERVATION")
        self.header_detail_var.set("Preparing a local session")
        self._sync_controls()

        def start():
            controller = None
            try:
                controller = self._factory(**settings)
                controller.start()
                self._messages.put(("started", controller, settings))
            except Exception as error:
                if controller is not None:
                    try:
                        controller.stop()
                        if hasattr(controller, "wait"):
                            controller.wait(timeout=15)
                    except Exception:
                        pass
                self._messages.put(("start-error", error, None))
        threading.Thread(target=start, name="apm-ui-start", daemon=True).start()

    def stop_observation(self):
        if not self._active or self._stopping or self.controller is None:
            return
        self._stopping = True
        self.header_detail_var.set("Stopping observation; attached processes continue")
        self._sync_controls()
        controller = self.controller

        def stop():
            try:
                controller.stop()
                if hasattr(controller, "wait") and not controller.wait(timeout=15):
                    raise TimeoutError("Observation worker has not finished flushing")
                self._messages.put(("stopped", None, None))
            except Exception as error:
                self._messages.put(("stop-error", error, None))
        threading.Thread(target=stop, name="apm-ui-stop", daemon=True).start()

    def _process_messages(self):
        for _ in range(8):
            try:
                kind, value, extra = self._messages.get_nowait()
            except queue.Empty:
                break
            if kind == "started":
                self.controller, self._starting, self._active = value, False, True
                self.clear_view(announce=False)
                self._received = 0
                self._session_started = datetime.now(timezone.utc)
                self._session_ended = None
                self._session_path = value.session_path
                self.header_var.set("DEMO SYNTHETIC" if extra["demo"] else "OBSERVATION ACTIVE")
                self.header_label.configure(foreground=PALETTE["amber"] if extra["demo"] else PALETTE["teal"])
                self.header_detail_var.set("Synthetic events · explicitly labelled" if extra["demo"] else "Scoped collection · recording locally")
                self.session_vars["Scope"].set(str(extra["workspace"]))
                self.session_vars["Process"].set(str(extra["pid"]) if extra["pid"] else "No process attached")
                self.session_vars["Location"].set(str(self._session_path))
                self.footer_var.set("Observation is active. Pause display affects only this view; Stop observation never stops the attached process.")
                if self._closing or self._pending_session:
                    self.stop_observation()
            elif kind == "start-error":
                self._starting = False
                self.header_var.set("OBSERVATION NOT STARTED")
                self.header_detail_var.set("Review the selected workspace and mode")
                self._error("Could not start observation", value)
            elif kind == "stopped":
                self._active = self._stopping = False
                self._session_ended = datetime.now(timezone.utc)
                if getattr(self.controller, "status", None) == "error":
                    self.header_var.set("OBSERVATION ERROR")
                    self.header_label.configure(foreground=PALETTE["red"])
                    self.header_detail_var.set("Recording ended with an error; session evidence retained")
                    self._error("Controller reported: " + str(getattr(self.controller, "error", None) or "Unknown recording error")[:240])
                else:
                    self.header_var.set("DEMO SYNTHETIC" if getattr(self.controller, "demo", False) else "OBSERVATION STOPPED")
                    self.header_detail_var.set("Session complete · recorder flushed")
                    self.footer_var.set("Observation stopped. The recorded session is preserved.")
            elif kind == "stop-error":
                self._stopping = False
                self.header_detail_var.set("Stop could not be confirmed; retry Stop observation")
                self._error("Observation stop requires attention", value)
            elif kind == "loaded":
                self._loading = False
                self._install_replay(value, extra)
            elif kind == "load-error":
                self._loading = False
                self._error("Could not read the selected session", value)
            self._sync_controls()
        if self._pending_session and not (self._active or self._starting or self._stopping or self._loading):
            path, self._pending_session = self._pending_session, None
            self._load_session(path)

    def _consume(self, events):
        dirty_categories = False
        latest = None
        for event in events:
            key, data, expired = self.buffer.add(event)
            self._received += 1
            latest = data
            if self._replay_mode and self._replay_engine is not None:
                # Pure state reconstruction from recorded, already-redacted evidence.
                # Mapping fixtures follow the same field contract without creating observers.
                defaults = dict(source="unknown", category="unknown", action="UNKNOWN", target="",
                                status="unknown", confidence=0.0, event_id="", timestamp="", metadata={})
                self._replay_engine.accept(SimpleNamespace(**(defaults | data)))
            if expired and self.tree.exists(expired) and not self.paused_var.get():
                self.tree.delete(expired)
                self._display_events.pop(expired, None)
            if not self.paused_var.get() and matches(data, self.category_var.get(), self.status_var.get(), self.search_var.get()):
                self._insert_row(key, data)
            if self.paused_var.get():
                self._paused_new += 1
            if data.get("category") not in self.category_box["values"]:
                dirty_categories = True
            metadata = data.get("metadata", {})
            if isinstance(metadata, dict) and (data.get("category") == "system" or metadata.get("scope") == "system_aggregate"):
                self._last_metadata = metadata
                if not self.paused_var.get():
                    self._show_telemetry(metadata)
        if dirty_categories:
            categories = sorted({str(data.get("category", "unknown")) for _, data in self.buffer.rows})
            self.category_box.configure(values=["All categories", *categories])
        if latest and self._replay_mode and not self.paused_var.get():
            self._replay_clock = timestamp(latest.get("timestamp"))
            self._refresh_replay_state()
        self._update_counts()

    def _insert_row(self, key, data):
        self._display_events[key] = data
        self.tree.insert("", "end", iid=key,
                         values=(clock_text(data.get("timestamp")), data.get("category", "unknown"),
                                 data.get("action", "UNKNOWN"), str(data.get("target", ""))[:240], data.get("status", "unknown")),
                         tags=(str(data.get("status", "unknown")),))

    def _update_counts(self):
        suffix = f" · paused, {self._paused_new:,} new" if self.paused_var.get() else ""
        self.count_var.set(f"{len(self.tree.get_children()):,} visible · {len(self.buffer):,} buffered{suffix}")
        self.session_vars["Received"].set(f"{self._received:,}" + (f" · replay {self._replay_index:,}/{len(self._replay_events):,}" if self._replay_mode else ""))

    def _schedule_filter(self, *_):
        if self._filter_timer:
            self.root.after_cancel(self._filter_timer)
        self._filter_timer = self.root.after(180, self._apply_filter)

    def _apply_filter(self):
        if self._filter_timer:
            self.root.after_cancel(self._filter_timer)
        self._filter_timer = None
        if self.paused_var.get():
            self.footer_var.set("Display paused. The updated filter will apply when the display resumes.")
            return
        selected = self.tree.selection()
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)
        self._display_events.clear()
        for key, data in self.buffer.filtered(self.category_var.get(), self.status_var.get(), self.search_var.get()):
            self._insert_row(key, data)
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected[0])
        elif selected:
            self._selected = None
            self._show_details()
        self._update_counts()

    def toggle_pause(self):
        if not self.paused_var.get():
            self._paused_new = 0
            self._apply_filter()
            self._show_telemetry(self._last_metadata)
            self._refresh_replay_state()
            self.footer_var.set("Display resumed. Session recording was unaffected.")
        else:
            self.footer_var.set("Display paused. Collection and session recording continue; the view retains the latest 2,000 events.")
        self._update_counts()

    def clear_view(self, announce=True):
        self.buffer.clear()
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)
        self._selected = None
        self._display_events.clear()
        self._paused_new = 0
        self._show_details()
        self._update_counts()
        if announce:
            self.footer_var.set("View cleared. No session file or recorded event was deleted.")

    def _selection_changed(self, _event=None):
        selection = self.tree.selection()
        if selection:
            self._selected = self._display_events.get(selection[0])
        self._show_details()

    def _show_details(self):
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", event_lens(self._selected, self.lens_var.get()))
        self.details.configure(state="disabled")

    def _show_telemetry(self, metadata):
        cpu = metadata.get("cpu_percent")
        self.telemetry_vars["CPU"].set(f"{cpu:.1f}%" if isinstance(cpu, (int, float)) else "Unavailable")
        ram = metadata.get("ram_percent")
        self.telemetry_vars["RAM"].set((f"{ram:.1f}% · " if isinstance(ram, (int, float)) else "") + bytes_text(metadata.get("ram_available_bytes")) + " free")
        self.telemetry_vars["DISK I/O"].set("R " + bytes_text(metadata.get("disk_read_bytes_per_sec"), True) + "\nW " + bytes_text(metadata.get("disk_write_bytes_per_sec"), True))
        self.telemetry_vars["NETWORK"].set("↓ " + bytes_text(metadata.get("network_received_bytes_per_sec"), True) + "\n↑ " + bytes_text(metadata.get("network_sent_bytes_per_sec"), True))
        self.telemetry_vars["GPU"].set("Unavailable\nNo GPU probe")

    def _refresh_live_info(self):
        if self.controller is None or self._replay_mode:
            return
        info = getattr(self.controller, "session_info", {}) or {}
        self._session_started = timestamp(info.get("started_at")) or self._session_started
        controller_status = str(getattr(self.controller, "status", "unknown"))
        if self._active and not self._stopping and controller_status in {"stopped", "error"}:
            if controller_status == "error":
                self.header_var.set("OBSERVATION ERROR")
                self.header_label.configure(foreground=PALETTE["red"])
            self.stop_observation()  # wait()/flush runs on a lifecycle thread, never Tk.
        self.session_vars["Session"].set(str(info.get("session_id", getattr(self._session_path, "name", "—"))))
        self.session_vars["Dropped"].set(str(getattr(self.controller, "dropped_count", 0)))
        state = getattr(self.controller, "current_state", None)
        if state is not None and not self.paused_var.get():
            data = state.to_dict() if hasattr(state, "to_dict") else dict(state)
            self.activity_var.set(str(data.get("state", "UNKNOWN")).replace("_", " ")[:40])
            self.activity_detail_var.set(str(data.get("summary", "No summary supplied"))[:240])
            self._state_time = timestamp(data.get("timestamp"))

    def _refresh_replay_state(self):
        if not self._replay_mode or self._replay_engine is None or self.paused_var.get():
            return
        state = self._replay_engine.current.to_dict()
        self.activity_var.set(str(state.get("state", "UNKNOWN")).replace("_", " ")[:40])
        self.activity_detail_var.set("Recorded · " + str(state.get("summary", "No recorded state evidence"))[:230])
        self._state_time = timestamp(state.get("timestamp"))

    def choose_session(self):
        path = filedialog.askdirectory(parent=self.root, title="Open recorded session folder — passive replay", initialdir=self.sessions_var.get())
        if path:
            self.open_session(path)

    def open_session(self, path):
        if self._loading or self._closing:
            return
        self._pending_session = Path(path)
        self._replay_playing = False
        if self._active:
            self.stop_observation()
        elif not (self._starting or self._stopping):
            pending, self._pending_session = self._pending_session, None
            self._load_session(pending)

    def _load_session(self, path):
        self._loading = True
        self.footer_var.set("Reading the selected session. Replay never starts adapters or executes recorded commands.")
        self._sync_controls()

        def load():
            try:
                self._messages.put(("loaded", self._reader(path), path))
            except Exception as error:
                self._messages.put(("load-error", error, None))
        threading.Thread(target=load, name="apm-ui-read-session", daemon=True).start()

    def _install_replay(self, result, path):
        info, events, warnings = result
        self.controller = None
        self._replay_mode, self._replay_playing = True, False
        self._replay_info, self._replay_events = dict(info), list(events)
        self._replay_engine = replay_state_engine()
        self._last_metadata = {}
        self._replay_index = self._received = 0
        self._replay_elapsed = 0.0
        self._session_path = path
        self._session_started = self._session_ended = self._state_time = self._replay_clock = None
        self.clear_view(announce=False)
        self.header_var.set("REPLAY PASSIVE")
        self.header_label.configure(foreground=PALETTE["muted"])
        self.header_detail_var.set("Recorded evidence · no observers or commands")
        self.activity_var.set("Session ready to replay")
        self.activity_detail_var.set("Press Play replay. Playback presents recorded events without repeating their actions.")
        self.session_vars["Session"].set(str(info.get("session_id", path.name)))
        self.session_vars["Location"].set(str(path))
        self.session_vars["Scope"].set(str(info.get("workspace", "Recorded scope")))
        self.session_vars["Process"].set("Passive replay · not attached")
        self.session_vars["Dropped"].set("Not applicable")
        for variable in self.telemetry_vars.values():
            variable.set("Awaiting recorded sample")
        self.footer_var.set(f"Loaded {len(events):,} events. " + (f"Reader reported {len(warnings)} warning(s); inspect session details. " if warnings else "") + "Instant reconstructs every event in bounded batches; the view retains the latest 2,000.")
        if warnings:
            self._selected = {"action": "SESSION_WARNINGS", "target": str(path), "status": "unknown", "interpretation_level": "observation", "metadata": {"reader_warnings": warnings}}
            self.lens_var.set("Evidence")
            self._show_details()
        self._sync_controls()

    def toggle_replay(self):
        if not self._replay_mode or not self._replay_events:
            return
        if self._replay_playing:
            self._replay_elapsed = self._playback_seconds()
            self._replay_playing = False
        else:
            if self._replay_index >= len(self._replay_events):
                self.stop_replay()
            speed = 4 if self.speed_var.get() == "4×" else 1
            self._replay_anchor = time.monotonic() - self._replay_elapsed / speed
            self._replay_playing = True
        self._sync_controls()

    def _playback_seconds(self):
        return (time.monotonic() - self._replay_anchor) * (4 if self.speed_var.get() == "4×" else 1)

    def _speed_changed(self):
        if self._replay_playing:
            self._replay_anchor = time.monotonic() - self._replay_elapsed / (4 if self.speed_var.get() == "4×" else 1)

    def _pump_replay(self):
        if not self._replay_playing:
            return
        origin = timestamp(event_dict(self._replay_events[0]).get("timestamp"))
        elapsed = self._playback_seconds()
        batch = []
        while self._replay_index < len(self._replay_events) and len(batch) < 200:
            event = self._replay_events[self._replay_index]
            moment = timestamp(event_dict(event).get("timestamp"))
            if self.speed_var.get() != "Instant" and origin and moment and (moment - origin).total_seconds() > elapsed:
                break
            batch.append(event)
            self._replay_index += 1
        self._consume(batch)
        if self.speed_var.get() == "Instant" and batch and origin:
            final_moment = timestamp(event_dict(batch[-1]).get("timestamp"))
            elapsed = max(0.0, (final_moment - origin).total_seconds()) if final_moment else elapsed
        self._replay_elapsed = elapsed
        if origin and not self.paused_var.get():
            self._replay_clock = origin + timedelta(seconds=elapsed)
        if self._replay_index == len(self._replay_events):
            self._replay_playing = False
            self.header_detail_var.set("Playback complete · no actions executed")
            self._sync_controls()

    def stop_replay(self):
        if not self._replay_mode:
            return
        self._replay_playing = False
        self._replay_index = self._received = 0
        self._replay_elapsed = 0.0
        self._replay_clock = self._state_time = None
        self._replay_engine = replay_state_engine()
        self._last_metadata = {}
        self.clear_view(announce=False)
        self.activity_var.set("Replay reset")
        self.activity_detail_var.set("Recorded events remain unchanged. Press Play replay to start again.")
        self._sync_controls()

    def leave_replay(self):
        if not self._replay_mode:
            return
        self._replay_mode = self._replay_playing = False
        self._replay_events = []
        self._replay_engine = None
        self.clear_view(announce=False)
        self.header_var.set("READY TO OBSERVE")
        self.header_label.configure(foreground=PALETTE["teal"])
        self.header_detail_var.set("No observation is running")
        self.activity_var.set("Waiting for your start")
        self.activity_detail_var.set("Choose the workspace and mode, then Start observation.")
        self._state_time = self._session_started = self._session_ended = None
        self._sync_controls()

    def _tick(self):
        self._timer = None
        try:
            self._process_messages()
            if self.controller is not None and not self._replay_mode:
                self._consume(self.controller.drain(limit=200))
                self._refresh_live_info()
            self._pump_replay()
            now = self._replay_clock if self._replay_mode else self._session_ended or datetime.now(timezone.utc)
            self.duration_var.set(duration_text((now - self._state_time).total_seconds()) if now and self._state_time else "—")
            self.session_vars["Elapsed"].set(duration_text(self._replay_elapsed) + " recorded" if self._replay_mode else duration_text(((self._session_ended or datetime.now(timezone.utc)) - self._session_started).total_seconds()) if self._session_started else "—")
        except Exception as error:
            self._error("A display update could not be completed", error)
        if self._closing and not (self._active or self._starting or self._stopping):
            self._destroy()
            return
        self._timer = self.root.after(150, self._tick)

    def close(self):
        self._closing = True
        self._pending_session = None
        self._replay_playing = False
        if self._active:
            self.stop_observation()
        elif not (self._starting or self._stopping):
            self._destroy()

    def _destroy(self):
        for identifier in (self._timer, self._filter_timer):
            if identifier:
                self.root.after_cancel(identifier)
        self._timer = self._filter_timer = None
        self.root.destroy()


def run_gui(workspace=None, sessions_root=None, pid=None, demo=False, session=None):
    root = tk.Tk()
    app = APMWindow(root, workspace, sessions_root, pid, demo)
    if session is not None:
        root.after(80, lambda: app.open_session(session))
    elif demo:
        root.after(80, app.start_observation)
    root.mainloop()
    return 0
