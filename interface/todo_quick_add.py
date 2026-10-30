"""
Quick add: a small window for capturing many todos in a row.

    Enter       add the todo, the field clears and stays ready for the next one
    Paste       several lines at once -> one todo per line
    Ctrl+Z      undo the last add
    Ctrl+L      open the full list
    Esc         close

The same syntax as in the list: text #tag !! @tomorrow
"""
from __future__ import annotations

import time
import tkinter as tk
from datetime import date

from interface.todo_window import (
    ACCENT,
    GRAY,
    PlaceholderEntry,
    bring_to_front,
    describe,
    read_clipboard_lines,
)
from scripts.todo_manager import TodoManager

RECENT_LIMIT = 5


class QuickAdd:

    def __init__(self, root: tk.Misc, manager: TodoManager, open_list=None):
        self.root = root
        self.manager = manager
        self.open_list = open_list

        self.win: tk.Toplevel | None = None
        self._opened_at = 0.0

        # ids added during this session of the window, newest last
        self._recent: list[str] = []
        self._added_total = 0

        # one entry per Enter / paste, so Ctrl+Z undoes exactly one of them
        self._batches: list[list[str]] = []

    # =========================================================
    # open / close
    # =========================================================

    def toggle(self):
        if self._is_open():
            self.close()
        else:
            self.open()

    def _is_open(self) -> bool:
        return self.win is not None and bool(self.win.winfo_exists())

    def close(self):
        if self._is_open():
            self.win.destroy()

        self.win = None

    def open(self):
        if self._is_open():
            bring_to_front(self.win)
            self.entry.prepare()
            return

        self._recent = []
        self._added_total = 0
        self._batches = []
        self._opened_at = time.monotonic()

        win = tk.Toplevel(self.root)
        self.win = win

        win.overrideredirect(True)
        win.attributes("-topmost", True)

        width = 620
        x = (win.winfo_screenwidth() - width) // 2
        y = win.winfo_screenheight() // 5

        win.geometry(f"{width}x90+{x}+{y}")

        frame = tk.Frame(win, bd=1, relief="solid", padx=14, pady=10)
        frame.pack(fill="both", expand=True)

        row = tk.Frame(frame)
        row.pack(fill="x")

        tk.Label(row, text="＋", fg=ACCENT, font=("Segoe UI", 18, "bold")).pack(side="left")

        self.entry = PlaceholderEntry(
            row,
            "New todo…   #tag  !!  @tomorrow",
            font=("Segoe UI", 16),
            bd=0,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.recent_label = tk.Label(
            frame, text="", fg=GRAY, font=("Segoe UI", 10),
            justify="left", anchor="w",
        )

        self.hint_label = tk.Label(
            frame,
            text="Enter add  ·  paste many lines  ·  Ctrl+Z undo  ·  Ctrl+L open list  ·  Esc close",
            fg=GRAY, font=("Segoe UI", 8), anchor="w",
        )
        self.hint_label.pack(fill="x", pady=(6, 0))

        self.entry.bind("<Return>", self.on_enter)
        self.entry.bind("<<Paste>>", self.on_paste)

        win.bind("<Escape>", lambda event: self.close())
        win.bind("<Control-z>", self.on_undo)
        win.bind("<Control-l>", self.on_open_list)
        win.bind("<FocusOut>", self._on_focus_out)

        self._render_recent()

        win.update_idletasks()

        bring_to_front(win)
        self.entry.prepare()

    def _on_focus_out(self, _event):
        # the window loses focus right after it opens on Windows - ignore that
        if time.monotonic() - self._opened_at < 0.4:
            return

        self.root.after(150, self._close_if_idle)

    def _close_if_idle(self):
        # never throw away a half-typed todo
        if (
            self._is_open()
            and self.win.focus_displayof() is None
            and not self.entry.value()
        ):
            self.close()

    # =========================================================
    # adding
    # =========================================================

    def add_lines(self, lines: list[str]):
        created = self.manager.add_many(lines)

        if not created:
            return

        ids = [todo.id for todo in created]

        self._batches.append(ids)
        self._recent.extend(ids)
        self._recent = self._recent[-RECENT_LIMIT:]
        self._added_total += len(ids)

        self.entry.clear()
        self.entry.prepare()

        self._render_recent()

    def on_enter(self, event=None):
        self.add_lines(self.entry.value().splitlines())

        return "break"

    def on_paste(self, event=None):
        lines = read_clipboard_lines(self.entry)

        if len(lines) > 1:
            self.add_lines(lines)

            return "break"

        if self.entry.selection_present():
            self.entry.delete("sel.first", "sel.last")

        self.entry.prepare()

        if lines:
            self.entry.insert("insert", lines[0].strip())

        return "break"

    def on_undo(self, event=None):
        # only what was added in this window; other changes are not touched
        if not self._batches:
            return "break"

        if not self.manager.undo():
            return "break"

        removed = self._batches.pop()

        self._recent = [i for i in self._recent if i not in removed]
        self._added_total = max(0, self._added_total - len(removed))

        self._render_recent()

        return "break"

    def on_open_list(self, event=None):
        self.close()

        if self.open_list is not None:
            self.root.after(30, self.open_list)

        return "break"

    # =========================================================
    # feedback
    # =========================================================

    def _render_recent(self):
        today = date.today()
        lines = []

        for todo_id in self._recent:
            todo = self.manager.get(todo_id)

            if todo is None:
                continue

            meta = describe(todo, today)
            lines.append(f"✓  {todo.text}" + (f"      {meta}" if meta else ""))

        if lines:
            if self._added_total > len(lines):
                lines.insert(0, f"…  {self._added_total - len(lines)} more added earlier")

            self.recent_label.config(text="\n".join(lines))
            self.recent_label.pack(fill="x", pady=(8, 0), before=self.hint_label)
        else:
            self.recent_label.pack_forget()

        self.win.update_idletasks()

        self.win.geometry(
            f"{self.win.winfo_width()}x{self.win.winfo_reqheight()}"
        )
