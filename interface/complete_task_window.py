from __future__ import annotations

import queue
import threading
import tkinter as tk

from tkinter import ttk, messagebox

from interface.ui_utils import attach, bring_to_front
from scripts.complete_task import complete_task, list_projects, target_path
from scripts.settings_manager import get_dirs


class CompleteTaskWindow:
    POLL_MS = 150

    def __init__(self, root, base_dir, settings=None):
        self.root = root

        dirs = get_dirs(base_dir, settings or {})
        self.active_dir = dirs["active"]
        self.backup_dir = dirs["active"] / 'backup'
        self.destinations = {
            "Complete": dirs["complete"],
            "Tests": dirs["tests"],
        }

        self.events = queue.Queue()
        self.busy = False
        self.closed = False

        self.window = tk.Toplevel(root)
        self.window.title("Complete task")
        self.window.geometry("640x560")
        self.window.minsize(560, 480)
        self.window.protocol("WM_DELETE_WINDOW", self._close)
        attach(self.window, root)

        self._build_ui()
        self._reload()
        self._poll()
        bring_to_front(self.window)

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def _build_ui(self):
        win = self.window
        win.columnconfigure(0, weight=1)
        win.rowconfigure(1, weight=1)

        header = ttk.Frame(win, padding=(12, 10, 12, 4))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header, text="COMPLETE TASK", font=("Arial", 15, "bold")
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="Refresh", command=self._reload).grid(
            row=0, column=1
        )
        ttk.Label(
            header, text=str(self.active_dir), foreground="#666666"
        ).grid(row=1, column=0, columnspan=2, sticky="w")

        box = ttk.Frame(win, padding=(12, 4))
        box.grid(row=1, column=0, sticky="nsew")
        box.columnconfigure(0, weight=1)
        box.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            box, columns=("name", "modified"), show="headings",
            selectmode="browse",
        )
        self.tree.heading("name", text="Project in active")
        self.tree.heading("modified", text="Changed")
        self.tree.column("name", width=360)
        self.tree.column("modified", width=150, anchor="center")

        ybar = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ybar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._update_summary())

        options = ttk.LabelFrame(win, text="What to do", padding=10)
        options.grid(row=2, column=0, sticky="ew", padx=12, pady=(8, 4))
        options.columnconfigure(1, weight=1)

        ttk.Label(options, text="Move to").grid(row=0, column=0, sticky="w")
        self.dest_var = tk.StringVar(value="Complete")
        combo = ttk.Combobox(
            options, textvariable=self.dest_var, state="readonly",
            values=list(self.destinations), width=14,
        )
        combo.grid(row=0, column=1, sticky="w", padx=8)
        combo.bind("<<ComboboxSelected>>", lambda e: self._update_summary())

        self.mode_var = tk.StringVar(value="folder")
        ttk.Radiobutton(
            options, text="Move the folder as it is",
            variable=self.mode_var, value="folder",
            command=self._update_summary,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Radiobutton(
            options,
            text="Pack into a .zip archive (the folder in active is removed)",
            variable=self.mode_var, value="zip",
            command=self._update_summary,
        ).grid(row=2, column=0, columnspan=2, sticky="w")

        self.snapshot_var = tk.BooleanVar(value=False)
        # ttk.Checkbutton(
        #     options,
        #     text="Create a backup snapshot first (zip, without .venv, "
        #          "node_modules, __pycache__)",
        #     variable=self.snapshot_var, command=self._update_summary,
        # ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.summary_label = ttk.Label(
            win, text="", wraplength=600, justify="left", foreground="#444444"
        )
        self.summary_label.grid(row=3, column=0, sticky="w", padx=12, pady=(4, 0))

        bottom = ttk.Frame(win, padding=(12, 8))
        bottom.grid(row=4, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Select a project.")
        ttk.Label(bottom, textvariable=self.status_var).grid(
            row=0, column=0, sticky="w"
        )

        self.complete_button = ttk.Button(
            bottom, text="Complete task", command=self._complete
        )
        self.complete_button.grid(row=0, column=1)

    # --------------------------------------------------
    # DATA
    # --------------------------------------------------

    def _reload(self):
        selected = self._selected_name()
        self.tree.delete(*self.tree.get_children())

        for project in list_projects(self.active_dir):
            self.tree.insert(
                "", "end", iid=project.name,
                values=(project.name, f"{project.modified:%d.%m.%Y %H:%M}"),
            )

        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected)

        if not self.tree.get_children():
            self.status_var.set(f"No projects in {self.active_dir}")

        self._update_summary()

    def _selected_name(self):
        selection = self.tree.selection()
        return selection[0] if selection else None

    def _update_summary(self):
        name = self._selected_name()

        if not name:
            self.summary_label.config(text="")
            return

        dest_dir = self.destinations[self.dest_var.get()]
        mode = self.mode_var.get()
        lines = [f"Result: {target_path(dest_dir, name, mode)}"]

        if self.snapshot_var.get():
            lines.append(f"Backup snapshot in: {self.backup_dir}")

        self.summary_label.config(text="\n".join(lines))

    # --------------------------------------------------
    # ACTION
    # --------------------------------------------------

    def _complete(self):
        if self.busy:
            return

        name = self._selected_name()
        if not name:
            messagebox.showinfo(
                "Complete task", "Select a project first.", parent=self.window
            )
            return

        dest_label = self.dest_var.get()
        dest_dir = self.destinations[dest_label]
        mode = self.mode_var.get()
        # snapshot = self.snapshot_var.get()
        snapshot = False
        on_conflict = "error"

        target = target_path(dest_dir, name, mode)

        if target.exists():
            if not messagebox.askyesno(
                "Already exists",
                f"'{target.name}' already exists in {dest_label}.\n\n"
                "Save this one under a new name with today's date?",
                parent=self.window,
            ):
                return
            on_conflict = "suffix"

        steps = []
        if snapshot:
            steps.append("create a backup snapshot")
        steps.append(
            "pack the project into a zip and remove the folder"
            if mode == "zip" else "move the folder"
        )

        if not messagebox.askyesno(
            "Complete task",
            f"Project: {name}\nTo: {dest_label} ({dest_dir})\n\n"
            f"The program will {', then '.join(steps)}.\n\nContinue?",
            parent=self.window,
        ):
            return

        self.busy = True
        self.complete_button.state(["disabled"])
        self.status_var.set("Working...")

        def log(message):
            self.events.put(("log", message))

        def worker():
            try:
                result = complete_task(
                    self.active_dir, name, dest_dir, self.backup_dir,
                    mode, snapshot, on_conflict, log,
                )
                self.events.put(("done", result, None))
            except Exception as error:
                self.events.put(("done", None, error))

        threading.Thread(target=worker, daemon=True).start()

    def _poll(self):
        if self.closed:
            return

        try:
            while True:
                event = self.events.get_nowait()

                if event[0] == "log":
                    self.status_var.set(event[1])

                elif event[0] == "done":
                    self._finished(event[1], event[2])

        except queue.Empty:
            pass

        try:
            self.window.after(self.POLL_MS, self._poll)
        except tk.TclError:
            pass

    def _finished(self, result, error):
        self.busy = False
        self.complete_button.state(["!disabled"])
        self._reload()

        if error:
            hint = ""
            if isinstance(error, PermissionError):
                hint = (
                    "\n\nA file or folder is probably open in another program "
                    "(Excel, VS Code, Explorer, a terminal). Close it and try again."
                )

            self.status_var.set("Failed.")
            messagebox.showerror(
                "Complete task",
                f"{type(error).__name__}: {error}{hint}\n\n"
                "Your project was not changed.",
                parent=self.window,
            )
            return

        lines = [f"Done: {result.destination}"]

        # if result.backup:
        #     lines.append(f"Backup snapshot: {result.backup}")

        self.status_var.set("Done.")

        if result.warnings:
            messagebox.showwarning(
                "Complete task",
                "\n".join(lines) + "\n\n" + "\n".join(result.warnings[:12]),
                parent=self.window,
            )
        else:
            messagebox.showinfo(
                "Complete task", "\n".join(lines), parent=self.window
            )

    def _close(self):
        if self.busy and not messagebox.askyesno(
            "Complete task",
            "The operation is still running. Close the window anyway?\n"
            "(it will keep running in the background)",
            parent=self.window,
        ):
            return

        self.closed = True
        self.window.destroy()


_instance = None


def open_complete_task(root, base_dir, settings=None):
    global _instance

    if _instance is not None and not _instance.closed:
        try:
            _instance._reload()
            bring_to_front(_instance.window)
            return _instance
        except tk.TclError:
            pass

    _instance = CompleteTaskWindow(root, base_dir, settings)
    return _instance
