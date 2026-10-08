from __future__ import annotations

import os
import re
import subprocess
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, simpledialog
from typing import Callable

from scripts.registry import AppContext
from scripts.search import best_score
from scripts.settings_manager import get_dirs

MAX_RESULTS = 8
ICONS = {"module": "▣", "program": "▶", "command": "⌘", "note": "✎"}
KIND_ORDER = {"module": 0, "command": 1, "program": 2, "note": 3}
DANGEROUS = re.compile(r"\b(shutdown|restart|del|erase|rmdir|rd|format|rm|reg\s+delete)\b", re.I)


@dataclass
class Item:
    kind: str
    title: str
    subtitle: str
    run: Callable[[], None]
    keywords: tuple[str, ...] = ()
    body: str = ""


class Launcher:

    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.win: tk.Toplevel | None = None
        self._programs: dict | None = None      # Start menu shortcut cache
        self._items: list[Item] = []
        self._shown: list[Item] = []
        self._opened_at = 0.0

    # ---------------------------------------------------------
    # open / close
    # ---------------------------------------------------------

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
            return

        root = self.ctx.root
        self._items = self._collect_items()
        self._opened_at = time.monotonic()

        win = tk.Toplevel(root)
        self.win = win
        win.overrideredirect(True)
        win.attributes("-topmost", True)

        width = 640
        x = (win.winfo_screenwidth() - width) // 2
        y = win.winfo_screenheight() // 5
        win.geometry(f"{width}x80+{x}+{y}")

        frame = tk.Frame(win, bd=1, relief="solid", padx=8, pady=8)
        frame.pack(fill="both", expand=True)

        self.query = tk.StringVar()
        self.entry = tk.Entry(frame, textvariable=self.query, font=("Segoe UI", 16), bd=0)
        self.entry.pack(fill="x")

        self.listbox = tk.Listbox(
            frame, font=("Segoe UI", 12), height=MAX_RESULTS, bd=0,
            activestyle="none", exportselection=False,
        )
        # The list will appear when the results are available.

        self.query.trace_add("write", lambda *_: self._refresh())
        self.entry.bind("<Down>", lambda e: self._move(1) or "break")
        self.entry.bind("<Up>", lambda e: self._move(-1) or "break")
        self.entry.bind("<Tab>", lambda e: self._move(1) or "break")
        self.entry.bind("<Return>", lambda e: self._activate())
        self.listbox.bind("<Double-Button-1>", lambda e: self._activate())
        win.bind("<Escape>", lambda e: self.close())
        win.bind("<FocusOut>", self._on_focus_out)

        self._refresh()

        win.update_idletasks()
        win.focus_force()
        self.entry.focus_set()

    def _on_focus_out(self, _event):
        # Ignore the loss of focus immediately after opening (Windows likes to cause that)
        if time.monotonic() - self._opened_at < 0.4:
            return
        self.ctx.root.after(120, self._close_if_unfocused)

    def _close_if_unfocused(self):
        if self._is_open() and self.win.focus_displayof() is None:
            self.close()

    # ---------------------------------------------------------
    # search
    # ---------------------------------------------------------

    def _refresh(self):
        query = self.query.get().strip()

        if not query:
            results = [i for i in self._items if i.kind == "module"]
        else:
            scored = []
            for item in self._items:
                value = self._item_score(query, item)
                if value is not None:
                    scored.append((value, item))
            scored.sort(key=lambda p: (-p[0], KIND_ORDER[p[1].kind], p[1].title.lower()))
            results = [item for _, item in scored]

        self._shown = results[:MAX_RESULTS]

        self.listbox.delete(0, "end")
        for item in self._shown:
            sub = f"   ·  {item.subtitle}" if item.subtitle else ""
            self.listbox.insert("end", f" {ICONS[item.kind]}  {item.title}{sub}")

        if self._shown:
            self.listbox.selection_set(0)
            self.listbox.pack(fill="x", pady=(8, 0))
            rows = len(self._shown)
        else:
            self.listbox.pack_forget()
            rows = 0

        self.listbox.configure(height=max(rows, 1))
        self.win.update_idletasks()
        self.win.geometry(f"{self.win.winfo_width()}x{self.win.winfo_reqheight()}")

    @staticmethod
    def _item_score(query: str, item: Item) -> int | None:
        scores = []

        s = best_score(query, item.title)
        if s is not None:
            scores.append(s)

        for word in item.keywords:
            s = best_score(query, word)
            if s is not None:
                scores.append(int(s * 0.9))

        # The note text: exact substring match only, minimum 3 characters.
        if item.body and len(query) >= 3:
            s = best_score(query, item.body, fuzzy=False)
            if s is not None:
                scores.append(int(s * 0.3))

        return max(scores) if scores else None

    def _move(self, step: int):
        if not self._shown:
            return
        current = self.listbox.curselection()
        index = (current[0] if current else 0) + step
        index = max(0, min(index, len(self._shown) - 1))
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(index)
        self.listbox.see(index)

    def _activate(self):
        current = self.listbox.curselection()
        if not current:
            return "break"

        item = self._shown[current[0]]
        self.close()
        # After closing the window, so that utility dialogs/windows receive focus
        self.ctx.root.after(30, item.run)
        return "break"

    # ---------------------------------------------------------
    # sources
    # ---------------------------------------------------------

    def _collect_items(self) -> list[Item]:
        items: list[Item] = []
        items += self._module_items()
        items += self._command_items()
        items += self._program_items()
        items += self._note_items()
        return items

    def _module_items(self) -> list[Item]:
        from modules import build_modules

        return [
            Item("module", m.title, "", lambda m=m: m.run(self.ctx), keywords=m.keywords)
            for m in build_modules() if m.in_launcher
        ]

    def _program_items(self) -> list[Item]:
        if self._programs is None:
            try:
                from scripts.program_launcher import get_programs
                self._programs = get_programs()
            except Exception as error:
                print(f"[Launcher] cannot read programs: {error!r}")
                self._programs = {}

        def start(path):
            if hasattr(os, "startfile"):
                os.startfile(path)

        return [
            Item("program", name, "", lambda p=path: start(p))
            for name, path in self._programs.items()
        ]

    def _command_items(self) -> list[Item]:
        try:
            from scripts.quick_commands_manager import QuickCommandsManager
            manager = QuickCommandsManager(self.ctx.base_dir / "db" / "quick_commands.ini")
            commands = manager.get_commands()
        except Exception as error:
            print(f"[Launcher] cannot read quick commands: {error!r}")
            return []

        return [
            Item("command", f"{c.group}: {c.name}", c.command,
                 lambda c=c: self._run_command(c), keywords=(c.name, c.command))
            for c in commands
        ]

    def _note_items(self) -> list[Item]:
        notes = getattr(self.ctx.notes_manager, "notes", [])

        def first_line(text: str) -> str:
            for line in text.splitlines():
                if line.strip():
                    return line.strip()[:60]
            return ""

        def open_notes():
            from interface.quick_notes_window import open_notes as show
            show(self.ctx.root, self.ctx.notes_manager)

        return [
            Item("note", n.theme or "(no title)", first_line(n.note), open_notes, body=n.note)
            for n in notes
        ]

    # ---------------------------------------------------------
    # run quick command
    # ---------------------------------------------------------

    def _run_command(self, command):
        root = self.ctx.root
        text = command.command

        if command.parameter == "input":
            value = simpledialog.askstring(command.name, "Parameter:", parent=root)
            if value is None:
                return
            try:
                text = text.format(value)
            except (IndexError, KeyError, ValueError):
                messagebox.showerror("Error", "Failed to substitute parameter.", parent=root)
                return

        if DANGEROUS.search(text):
            if not messagebox.askyesno("Confirm", f"Execute?\n\n{text}", parent=root):
                return

        cwd = get_dirs(self.ctx.base_dir, self.ctx.settings)["working"]

        try:
            subprocess.Popen(text, cwd=cwd, shell=True)
        except Exception as error:
            messagebox.showerror("Execution error:", str(error), parent=root)
