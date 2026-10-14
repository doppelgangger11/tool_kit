from __future__ import annotations

import tkinter as tk

from datetime import date, datetime, timedelta
from tkinter import ttk, filedialog, messagebox, simpledialog

from interface.ui_utils import attach, bring_to_front
from scripts.complete_task import list_projects
from scripts.settings_manager import get_dirs
from scripts.time_tracker import (
    DAY_NAMES,
    STALE_HOURS,
    format_hm,
    format_hms,
    get_tracker,
    last_occurrence,
    parse_date_text,
    parse_time_text,
    week_start,
)


RED = "#c53030"
GRAY = "#666666"
GREEN = "#16803c"


class TimeTrackerWindow:
    """Тайм-трекер по проектам: таймер, отчёт за неделю, экспорт в CSV."""

    def __init__(self, root, base_dir, settings=None):
        self.root = root
        self.tracker = get_tracker(base_dir)
        self.active_dir = get_dirs(base_dir, settings or {})["active"]

        self.monday = week_start(date.today())
        self.closed = False
        self._seen_state = "unset"
        self._ticks = 0

        self.window = tk.Toplevel(root)
        self.window.title("Time Tracker")
        self.window.geometry("900x680")
        self.window.minsize(780, 560)
        self.window.protocol("WM_DELETE_WINDOW", self._close)
        attach(self.window, root)

        self._build_ui()
        self._refresh_all()
        self._tick()
        bring_to_front(self.window)

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def _build_ui(self):
        win = self.window
        win.columnconfigure(0, weight=1)
        win.rowconfigure(4, weight=1)

        ttk.Label(
            win, text="TIME TRACKER", font=("Arial", 15, "bold")
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        # ---- controls ----
        controls = ttk.Frame(win, padding=(12, 4))
        controls.grid(row=1, column=0, sticky="ew")
        controls.columnconfigure(1, weight=2)
        controls.columnconfigure(3, weight=2)

        ttk.Label(controls, text="Project").grid(row=0, column=0, sticky="w")
        self.project_var = tk.StringVar()
        self.project_combo = ttk.Combobox(controls, textvariable=self.project_var)
        self.project_combo.grid(row=0, column=1, sticky="ew", padx=(6, 12))

        ttk.Label(controls, text="Note").grid(row=0, column=2, sticky="w")
        self.note_var = tk.StringVar()
        note_entry = ttk.Entry(controls, textvariable=self.note_var)
        note_entry.grid(row=0, column=3, sticky="ew", padx=(6, 12))

        self.start_button = ttk.Button(controls, text="▶ Start", command=self._start)
        self.start_button.grid(row=0, column=4)

        self.stop_button = ttk.Button(controls, text="■ Stop", command=self._stop)
        self.stop_button.grid(row=0, column=5, padx=(6, 0))

        note_entry.bind("<Return>", lambda e: self._start())

        # ---- timer ----
        timer = ttk.Frame(win, padding=(12, 8))
        timer.grid(row=2, column=0, sticky="ew")
        timer.columnconfigure(0, weight=1)

        self.timer_label = ttk.Label(
            timer, text="00:00:00", font=("Consolas", 28, "bold")
        )
        self.timer_label.grid(row=0, column=0, sticky="w")

        self.timer_sub = ttk.Label(timer, text="", foreground=GRAY)
        self.timer_sub.grid(row=1, column=0, sticky="w")

        self.stale_frame = ttk.Frame(timer)
        self.stale_frame.grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Label(
            self.stale_frame, foreground=RED,
            text=f"The timer has been running for more than {STALE_HOURS} h. "
                 "Did you forget to stop it?",
        ).pack(side="left")
        ttk.Button(
            self.stale_frame, text="Stop at…", command=self._stop_at
        ).pack(side="left", padx=(8, 0))

        # ---- week navigation ----
        nav = ttk.Frame(win, padding=(12, 2))
        nav.grid(row=3, column=0, sticky="ew")

        ttk.Button(nav, text="◀", width=3, command=lambda: self._shift_week(-1)).pack(
            side="left"
        )
        self.week_label = ttk.Label(nav, text="", font=("Arial", 10, "bold"), width=34)
        self.week_label.pack(side="left", padx=8)
        ttk.Button(nav, text="▶", width=3, command=lambda: self._shift_week(1)).pack(
            side="left"
        )
        ttk.Button(nav, text="This week", command=self._this_week).pack(
            side="left", padx=(10, 0)
        )

        # ---- tables ----
        notebook = ttk.Notebook(win)
        notebook.grid(row=4, column=0, sticky="nsew", padx=12, pady=(4, 0))

        summary_tab = ttk.Frame(notebook)
        entries_tab = ttk.Frame(notebook)
        notebook.add(summary_tab, text="Week summary")
        notebook.add(entries_tab, text="Entries")

        for tab in (summary_tab, entries_tab):
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(0, weight=1)

        day_columns = [f"d{i}" for i in range(7)]
        self.summary = ttk.Treeview(
            summary_tab, columns=["project", *day_columns, "total"],
            show="headings", selectmode="browse",
        )
        self.summary.column("project", width=200, anchor="w")
        for column in day_columns:
            self.summary.column(column, width=66, anchor="center")
        self.summary.column("total", width=80, anchor="center")
        self.summary.heading("project", text="Project")
        self.summary.heading("total", text="Total")
        self.summary.tag_configure("total", font=("Arial", 9, "bold"))
        self.summary.grid(row=0, column=0, sticky="nsew")

        self.entries = ttk.Treeview(
            entries_tab,
            columns=("date", "project", "time", "duration", "note"),
            show="headings", selectmode="browse",
        )
        for column, title, width, anchor in (
            ("date", "Date", 90, "center"),
            ("project", "Project", 200, "w"),
            ("time", "Time", 110, "center"),
            ("duration", "Duration", 80, "center"),
            ("note", "Note", 300, "w"),
        ):
            self.entries.heading(column, text=title)
            self.entries.column(column, width=width, anchor=anchor)
        self.entries.tag_configure("running", foreground=GREEN)

        ybar = ttk.Scrollbar(entries_tab, orient="vertical", command=self.entries.yview)
        self.entries.configure(yscrollcommand=ybar.set)
        self.entries.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")

        # ---- bottom ----
        bottom = ttk.Frame(win, padding=(12, 8))
        bottom.grid(row=5, column=0, sticky="ew")

        ttk.Button(bottom, text="Add entry…", command=self._add_entry).pack(side="left")
        ttk.Button(bottom, text="Delete entry", command=self._delete_entry).pack(
            side="left", padx=(6, 0)
        )

        ttk.Button(bottom, text="Export entries", command=self._export_entries).pack(
            side="right"
        )
        ttk.Button(bottom, text="Export week summary", command=self._export_summary).pack(
            side="right", padx=(0, 6)
        )
        self.excel_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            bottom, text="Excel (RU): ';' and decimal comma", variable=self.excel_var
        ).pack(side="right", padx=(0, 12))

        self.status_var = tk.StringVar(value="")
        ttk.Label(win, textvariable=self.status_var, foreground=GRAY).grid(
            row=6, column=0, sticky="w", padx=12, pady=(0, 8)
        )

    # --------------------------------------------------
    # DATA / REFRESH
    # --------------------------------------------------

    def _project_names(self):
        names = {}

        for name in self.tracker.projects():
            names.setdefault(name.casefold(), name)

        for project in list_projects(self.active_dir):
            names.setdefault(project.name.casefold(), project.name)

        return sorted(names.values(), key=str.lower)

    def _refresh_projects(self):
        self.project_combo["values"] = self._project_names()

        if not self.project_var.get().strip():
            run = self.tracker.running()
            self.project_var.set(
                run["project"] if run else self.tracker.last_project()
            )

    def _state_key(self):
        run = self.tracker.running()
        return (run["project"], run["started"]) if run else None

    def _refresh_all(self):
        self._seen_state = self._state_key()
        self._refresh_projects()
        self._update_timer()
        self._refresh_tables()

    def _today_seconds(self):
        today = date.today()
        return sum(
            (e["end"] - e["start"]).total_seconds()
            for e in self.tracker.entries(today, today)
        )

    def _update_timer(self):
        run = self.tracker.running()
        today = format_hm(self._today_seconds())

        if run:
            now = datetime.now().astimezone()
            elapsed = (now - run["started"]).total_seconds()

            self.timer_label.config(text=format_hms(elapsed), foreground=GREEN)
            started = run["started"].astimezone()
            self.timer_sub.config(
                text=f"{run['project']} · started {started:%d.%m %H:%M} · "
                     f"today {today}"
            )
            self.stop_button.state(["!disabled"])

            if self.tracker.is_stale():
                self.stale_frame.grid()
            else:
                self.stale_frame.grid_remove()
        else:
            self.timer_label.config(text="00:00:00", foreground=GRAY)
            self.timer_sub.config(text=f"Not running · today {today}")
            self.stop_button.state(["disabled"])
            self.stale_frame.grid_remove()

    def _refresh_tables(self):
        sunday = self.monday + timedelta(days=6)
        iso_week = self.monday.isocalendar()[1]
        self.week_label.config(
            text=f"Week {iso_week}:  {self.monday:%d.%m} – {sunday:%d.%m.%Y}"
        )

        # summary
        for i in range(7):
            day = self.monday + timedelta(days=i)
            self.summary.heading(f"d{i}", text=f"{DAY_NAMES[i]} {day:%d.%m}")

        self.summary.delete(*self.summary.get_children())
        projects, table, totals = self.tracker.week_summary(self.monday)

        def cell(seconds):
            return format_hm(seconds) if seconds >= 30 else ""

        for project in projects:
            row = table[project]
            self.summary.insert(
                "", "end",
                values=[project, *[cell(s) for s in row], format_hm(sum(row))],
            )

        if projects:
            self.summary.insert(
                "", "end", tags=("total",),
                values=["TOTAL", *[cell(s) for s in totals], format_hm(sum(totals))],
            )

        # entries
        self.entries.delete(*self.entries.get_children())

        for e in self.tracker.entries(self.monday, sunday):
            seconds = (e["end"] - e["start"]).total_seconds()
            iid = "running" if e["running"] else str(e["id"])
            end_text = "…" if e["running"] else f"{e['end']:%H:%M}"

            self.entries.insert(
                "", "end", iid=iid,
                values=(
                    f"{e['start']:%d.%m.%Y}", e["project"],
                    f"{e['start']:%H:%M} – {end_text}",
                    format_hm(seconds), e["note"],
                ),
                tags=("running",) if e["running"] else (),
            )

    def _tick(self):
        if self.closed:
            return

        try:
            if self._state_key() != self._seen_state:
                # таймер запустили или остановили горячей клавишей
                self._refresh_all()
            else:
                self._update_timer()
                self._ticks += 1

                if (
                    self._seen_state is not None
                    and self._ticks % 15 == 0
                    and self.monday == week_start(date.today())
                ):
                    self._refresh_tables()

            self.window.after(1000, self._tick)
        except tk.TclError:
            pass

    # --------------------------------------------------
    # TIMER ACTIONS
    # --------------------------------------------------

    def _start(self):
        try:
            self.tracker.start(self.project_var.get(), self.note_var.get())
        except ValueError as error:
            messagebox.showwarning("Time Tracker", str(error), parent=self.window)
            return

        self.note_var.set("")
        self.status_var.set(f"Started: {self.tracker.running()['project']}")
        self._refresh_all()

    def _stop(self):
        run = self.tracker.running()
        entry = self.tracker.stop()

        if run:
            self.status_var.set(f"Stopped: {run['project']}")
        elif entry is None:
            self.status_var.set("The timer is not running.")

        self._refresh_all()

    def _stop_at(self):
        run = self.tracker.running()
        if not run:
            return

        text = simpledialog.askstring(
            "Stop at",
            "Time of the last real work (HH:MM).\n"
            "The timer will be stopped at that moment:",
            parent=self.window,
        )
        if not text:
            return

        try:
            moment = last_occurrence(
                parse_time_text(text),
                datetime.now().astimezone(),
                run["started"],
            )
        except ValueError as error:
            messagebox.showwarning("Time Tracker", str(error), parent=self.window)
            return

        self.tracker.stop(at=moment)
        self.status_var.set(f"Stopped at {moment:%d.%m %H:%M}")
        self._refresh_all()

    # --------------------------------------------------
    # WEEK
    # --------------------------------------------------

    def _shift_week(self, weeks):
        self.monday += timedelta(days=7 * weeks)
        self._refresh_tables()

    def _this_week(self):
        self.monday = week_start(date.today())
        self._refresh_tables()

    # --------------------------------------------------
    # ENTRIES
    # --------------------------------------------------

    def _add_entry(self):
        dlg = tk.Toplevel(self.window)
        dlg.title("Add entry")
        dlg.resizable(False, False)
        dlg.transient(self.window)

        frame = ttk.Frame(dlg, padding=14)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        project_var = tk.StringVar(value=self.project_var.get())
        date_var = tk.StringVar(value=f"{date.today():%d.%m.%Y}")
        start_var = tk.StringVar(value="09:00")
        end_var = tk.StringVar(value="10:00")
        note_var = tk.StringVar()

        ttk.Label(frame, text="Project").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Combobox(
            frame, textvariable=project_var, values=self._project_names(), width=32
        ).grid(row=0, column=1, sticky="ew", padx=(10, 0))

        for row, (label, var) in enumerate(
            (("Date", date_var), ("Start", start_var),
             ("End", end_var), ("Note", note_var)), start=1,
        ):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=3)
            ttk.Entry(frame, textvariable=var, width=34).grid(
                row=row, column=1, sticky="ew", padx=(10, 0)
            )

        ttk.Label(
            frame, foreground=GRAY,
            text="Date: 15.10.2026   Time: 09:30\n"
                 "Work past midnight: add two entries.",
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))

        def save():
            try:
                day = parse_date_text(date_var.get())
                start = datetime.combine(day, parse_time_text(start_var.get())).astimezone()
                end = datetime.combine(day, parse_time_text(end_var.get())).astimezone()
                self.tracker.add_entry(project_var.get(), start, end, note_var.get())
            except ValueError as error:
                messagebox.showwarning("Add entry", str(error), parent=dlg)
                return

            dlg.destroy()
            self.monday = week_start(day)
            self.status_var.set("Entry added.")
            self._refresh_all()

        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Add", command=save).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Cancel", command=dlg.destroy).pack(side="left")

        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.bind("<Return>", lambda e: save())

        try:
            dlg.wait_visibility()
            dlg.grab_set()
        except tk.TclError:
            pass

    def _delete_entry(self):
        selection = self.entries.selection()

        if not selection:
            messagebox.showinfo(
                "Time Tracker", "Select an entry on the Entries tab first.",
                parent=self.window,
            )
            return

        if selection[0] == "running":
            messagebox.showinfo(
                "Time Tracker", "This timer is still running. Stop it first.",
                parent=self.window,
            )
            return

        values = self.entries.item(selection[0], "values")

        if not messagebox.askyesno(
            "Delete entry",
            f"Delete this entry?\n\n{values[0]}  {values[1]}  {values[2]}  ({values[3]})",
            parent=self.window,
        ):
            return

        self.tracker.delete_entry(int(selection[0]))
        self.status_var.set("Entry deleted.")
        self._refresh_all()

    # --------------------------------------------------
    # EXPORT
    # --------------------------------------------------

    def _export(self, kind):
        iso = self.monday.isocalendar()
        filename = filedialog.asksaveasfilename(
            parent=self.window,
            title="Export to CSV",
            defaultextension=".csv",
            initialfile=f"time_{kind}_{iso[0]}-W{iso[1]:02d}.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return

        try:
            if kind == "summary":
                self.tracker.export_summary_csv(
                    filename, self.monday, self.excel_var.get()
                )
            else:
                self.tracker.export_entries_csv(
                    filename, self.monday, self.monday + timedelta(days=6),
                    self.excel_var.get(),
                )
        except OSError as error:
            messagebox.showerror("Time Tracker", str(error), parent=self.window)
            return

        self.status_var.set(f"Saved: {filename}")

    def _export_summary(self):
        self._export("summary")

    def _export_entries(self):
        self._export("entries")

    def _close(self):
        self.closed = True
        self.window.destroy()


_instance = None


def open_time_tracker(root, base_dir, settings=None):
    global _instance

    if _instance is not None and not _instance.closed:
        try:
            _instance._refresh_all()
            bring_to_front(_instance.window)
            return _instance
        except tk.TclError:
            pass

    _instance = TimeTrackerWindow(root, base_dir, settings)
    return _instance
