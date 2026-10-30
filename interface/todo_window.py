"""
Todo list window.

Keyboard:
    Enter (in the top field)  add; several lines can be pasted at once
    Down / Esc                go to the list / back to the field (Esc twice closes)
    Space                     done / reopen the selected todos
    F2 / Enter / double click edit in place (same syntax: text #tag !! @tomorrow)
    Delete                    delete the selected todos
    Ctrl+Z                    undo (works for everything, even "Clear done")
    Ctrl+1 / 2 / 3            Active / All / Done
    Ctrl+F                    search
    Just start typing         the text goes to the top field
"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from datetime import date, timedelta
from tkinter import ttk

from scripts.todo_manager import TodoManager, format_due

CHECK_OFF = "☐"
CHECK_ON = "☑"

HINT = "#tag   !  !!  !!!   @today  @tomorrow  @fri  @5.11"

GRAY = "#8a8a8a"
ACCENT = "#4a7bd0"
OVERDUE = "#c0392b"

PRIORITY_COLORS = {1: "#2e6bb0", 2: "#c77d0a", 3: "#b03a2e"}

ALL_TAGS = "All tags"

_window = None


# ---------------------------------------------------------
# shared widgets / helpers
# ---------------------------------------------------------

class PlaceholderEntry(tk.Entry):
    """An Entry that shows a grey hint while it is empty and unfocused."""

    def __init__(self, master, placeholder: str, **kwargs):
        super().__init__(master, **kwargs)

        self.placeholder = placeholder
        self._normal_fg = self.cget("fg")
        self._showing = False

        self.bind("<FocusIn>", self._on_focus_in, add="+")
        self.bind("<FocusOut>", self._on_focus_out, add="+")

        self._show_placeholder()

    def _show_placeholder(self):
        if tk.Entry.get(self):
            return

        self.insert(0, self.placeholder)
        self.config(fg=GRAY)
        self._showing = True

    def _hide_placeholder(self):
        if not self._showing:
            return

        self.delete(0, "end")
        self.config(fg=self._normal_fg)
        self._showing = False

    def _on_focus_in(self, _event=None):
        self._hide_placeholder()

    def _on_focus_out(self, _event=None):
        self._show_placeholder()

    def value(self) -> str:
        return "" if self._showing else tk.Entry.get(self)

    def clear(self):
        self._hide_placeholder()
        self.delete(0, "end")

        if self.focus_displayof() is not self:
            self._show_placeholder()

    def prepare(self):
        """Focus the field and make it ready for typing."""
        self.focus_set()
        self._hide_placeholder()


def bring_to_front(window: tk.Misc) -> None:
    """Windows does not always raise a window opened from a background hotkey."""
    try:
        window.deiconify()
        window.lift()
        window.attributes("-topmost", True)
        window.after(200, lambda: window.attributes("-topmost", False))
        window.focus_force()
    except tk.TclError:
        pass


def show_toast(root: tk.Misc, text: str, milliseconds: int = 1500) -> None:
    """A small message at the top of the screen that disappears by itself."""
    toast = tk.Toplevel(root)
    toast.overrideredirect(True)
    toast.attributes("-topmost", True)

    tk.Label(
        toast, text=text, bg="#2b2b2b", fg="#ffffff",
        font=("Segoe UI", 11), padx=18, pady=9,
    ).pack()

    toast.update_idletasks()

    x = (toast.winfo_screenwidth() - toast.winfo_reqwidth()) // 2
    y = toast.winfo_screenheight() // 8

    toast.geometry(f"+{x}+{y}")
    toast.after(milliseconds, toast.destroy)


def read_clipboard_lines(widget: tk.Misc) -> list[str]:
    try:
        text = widget.clipboard_get()
    except tk.TclError:
        return []

    return [line for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            if line.strip()]


def describe(todo, today: date) -> str:
    """Right column of a row: priority, due date, tags."""
    parts = []

    if todo.priority:
        parts.append("!" * todo.priority)

    label, overdue = format_due(todo.due, today)

    if label:
        parts.append(("⚠ " if overdue and not todo.done else "") + label)

    parts.extend(f"#{tag}" for tag in todo.tags)

    return "   ".join(parts)


# ---------------------------------------------------------
# window
# ---------------------------------------------------------

class TodoWindow:

    def __init__(self, root: tk.Misc, manager: TodoManager):
        self.root = root
        self.manager = manager

        self.window = tk.Toplevel(root)
        self.window.title("Todo")
        self.window.geometry("500x620")
        self.window.minsize(380, 340)

        self._flash_job = None
        self._editor = None

        self.mode = tk.StringVar(value="active")

        self._build_styles()
        self._build_ui()
        self._bind_keys()

        self.manager.subscribe(self.refresh)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.refresh()
        self.entry.prepare()

    # =========================================================
    # BUILD
    # =========================================================

    def _build_styles(self):
        style = ttk.Style(self.window)

        self.font = tkfont.Font(family="Segoe UI", size=11)
        self.font_bold = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.font_done = tkfont.Font(family="Segoe UI", size=11, overstrike=True)
        self.font_check = tkfont.Font(family="Segoe UI Symbol", size=14)

        style.configure("Todo.Treeview", rowheight=32, font=self.font, borderwidth=0)

        try:
            style.layout("Todo.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        except tk.TclError:
            pass

        # Tk 8.6.9 ignores the colours of tagged rows without this
        style.map(
            "Todo.Treeview",
            foreground=[
                item for item in style.map("Treeview", query_opt="foreground")
                if item[:2] != ("!disabled", "!selected")
            ],
            background=[
                item for item in style.map("Treeview", query_opt="background")
                if item[:2] != ("!disabled", "!selected")
            ],
        )

    def _build_ui(self):
        window = self.window

        top = tk.Frame(window, padx=14, pady=12)
        top.pack(fill="x")

        field = tk.Frame(
            top,
            highlightthickness=2,
            highlightbackground="#cfcfcf",
            highlightcolor=ACCENT,
        )
        field.pack(fill="x")

        tk.Label(field, text="＋", fg=ACCENT, font=("Segoe UI", 16, "bold")).pack(
            side="left", padx=(8, 0)
        )

        self.entry = PlaceholderEntry(
            field,
            "Add a todo…  press Enter",
            font=("Segoe UI", 13),
            relief="flat",
            bd=0,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=8, pady=8)

        tk.Label(top, text=HINT, fg=GRAY, font=("Segoe UI", 8), anchor="w").pack(
            fill="x", pady=(4, 0)
        )

        # ----- filters -----

        bar = tk.Frame(window, padx=14)
        bar.pack(fill="x")

        self.mode_buttons = {}

        for key, title in (("active", "Active"), ("all", "All"), ("done", "Done")):
            button = ttk.Radiobutton(
                bar,
                text=title,
                value=key,
                variable=self.mode,
                style="Toolbutton",
                command=self.refresh,
            )
            button.pack(side="left", padx=(0, 4))
            self.mode_buttons[key] = (button, title)

        self.search = PlaceholderEntry(
            bar, "Search", width=14, font=("Segoe UI", 10), relief="solid", bd=1
        )
        self.search.pack(side="right")
        self.search.bind("<KeyRelease>", lambda event: self.refresh())

        self.tag_var = tk.StringVar(value=ALL_TAGS)
        self.tag_box = ttk.Combobox(
            bar, textvariable=self.tag_var, values=[ALL_TAGS],
            state="readonly", width=11,
        )
        self.tag_box.pack(side="right", padx=(0, 6))
        self.tag_box.bind("<<ComboboxSelected>>", lambda event: self.refresh())

        # ----- list -----

        body = tk.Frame(window, padx=14, pady=8)
        body.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            body,
            style="Todo.Treeview",
            columns=("text", "meta"),
            show="tree",
            selectmode="extended",
        )

        self.tree.column("#0", width=44, stretch=False, anchor="center")
        self.tree.column("text", width=260, stretch=True)
        self.tree.column("meta", width=150, stretch=False, anchor="e")

        scroll = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)

        scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.tag_configure("done", foreground="#a0a0a0", font=self.font_done)
        self.tree.tag_configure("overdue", foreground=OVERDUE)

        for level, color in PRIORITY_COLORS.items():
            self.tree.tag_configure(f"p{level}", foreground=color)

        self.tree.tag_configure("p3", font=self.font_bold)

        self.empty_label = tk.Label(
            self.tree, text="", fg=GRAY, font=("Segoe UI", 11), justify="center"
        )

        # ----- footer -----

        footer = tk.Frame(window, padx=14, pady=(0))
        footer.pack(fill="x", pady=(0, 12))

        self.status = tk.Label(footer, text="", fg=GRAY, anchor="w", font=("Segoe UI", 9))
        self.status.pack(side="left", fill="x", expand=True)

        ttk.Button(footer, text="Clear done", command=self.clear_done).pack(side="right")
        self.undo_button = ttk.Button(footer, text="Undo", command=self.undo)
        self.undo_button.pack(side="right", padx=(0, 6))

        self.menu = self._build_menu()

    def _build_menu(self) -> tk.Menu:
        menu = tk.Menu(self.window, tearoff=False)

        menu.add_command(label="Done / Reopen    Space", command=self.toggle_selected)
        menu.add_command(label="Edit    F2", command=self.edit_selected)

        priority = tk.Menu(menu, tearoff=False)
        for level, title in ((0, "None"), (1, "!  low"), (2, "!!  medium"), (3, "!!!  high")):
            priority.add_command(
                label=title, command=lambda level=level: self.set_priority(level)
            )
        menu.add_cascade(label="Priority", menu=priority)

        due = tk.Menu(menu, tearoff=False)
        for title, days in (("Today", 0), ("Tomorrow", 1), ("In a week", 7)):
            due.add_command(label=title, command=lambda days=days: self.set_due(days))
        due.add_command(label="No date", command=lambda: self.set_due(None))
        menu.add_cascade(label="Due date", menu=due)

        menu.add_separator()
        menu.add_command(label="Delete    Del", command=self.delete_selected)

        return menu

    def _bind_keys(self):
        window = self.window

        # field
        self.entry.bind("<Return>", self.add_from_entry)
        self.entry.bind("<<Paste>>", self.on_paste)
        self.entry.bind("<Down>", self.focus_list)
        self.entry.bind("<Escape>", self.on_entry_escape)

        # list
        tree = self.tree

        tree.bind("<Button-1>", self.on_click)
        tree.bind("<Double-1>", self.on_double_click)
        tree.bind("<Button-3>", self.on_right_click)
        tree.bind("<space>", lambda event: self.toggle_selected() or "break")
        tree.bind("<Delete>", lambda event: self.delete_selected() or "break")
        tree.bind("<F2>", lambda event: self.edit_selected() or "break")
        tree.bind("<Return>", lambda event: self.edit_selected() or "break")
        tree.bind("<Control-a>", lambda event: tree.selection_set(tree.get_children()) or "break")
        tree.bind("<Escape>", lambda event: self.entry.prepare())
        tree.bind("<Key>", self.on_list_key)

        # whole window
        window.bind("<Control-z>", lambda event: self.undo())
        window.bind("<Control-f>", lambda event: self.search.prepare() or "break")
        window.bind("<Control-Key-1>", lambda event: self.set_mode("active"))
        window.bind("<Control-Key-2>", lambda event: self.set_mode("all"))
        window.bind("<Control-Key-3>", lambda event: self.set_mode("done"))

        self.search.bind("<Escape>", self.on_search_escape)
        self.search.bind("<Return>", self.focus_list)

    # =========================================================
    # LIFECYCLE
    # =========================================================

    def close(self):
        global _window

        self.manager.unsubscribe(self.refresh)

        if self._flash_job is not None:
            try:
                self.window.after_cancel(self._flash_job)
            except tk.TclError:
                pass

        _window = None
        self.window.destroy()

    # =========================================================
    # RENDER
    # =========================================================

    def current_tag(self) -> str | None:
        value = self.tag_var.get()

        if value == ALL_TAGS:
            return None

        return value.lstrip("#")

    def refresh(self):
        manager = self.manager

        # tags for the filter box
        tags = manager.tags()
        self.tag_box.config(values=[ALL_TAGS] + [f"#{tag}" for tag in tags])

        if self.current_tag() and self.current_tag() not in tags:
            self.tag_var.set(ALL_TAGS)

        mode = self.mode.get()
        items = manager.view(mode, self.current_tag(), self.search.value())

        selected = set(self.tree.selection())
        top = self.tree.yview()[0]

        self.tree.delete(*self.tree.get_children())

        today = date.today()

        widest = 0

        for todo in items:
            meta = describe(todo, today)

            widest = max(widest, self.font.measure(meta))

            self.tree.insert(
                "",
                "end",
                iid=todo.id,
                text=CHECK_ON if todo.done else CHECK_OFF,
                values=(todo.text, meta),
                tags=self.row_tags(todo, today),
            )

        # the right column is as wide as its longest content (but never eats the text)
        limit = max(110, int(self.tree.winfo_width() * 0.55))

        self.tree.column("meta", width=min(max(widest + 28, 90), limit))

        keep = [iid for iid in selected if self.tree.exists(iid)]

        if keep:
            self.tree.selection_set(keep)

        self.tree.yview_moveto(top)

        self.update_filters()
        self.update_empty_state(mode, bool(items))
        self.update_footer()

    @staticmethod
    def row_tags(todo, today: date) -> tuple[str, ...]:
        if todo.done:
            return ("done",)

        tags = []

        _, overdue = format_due(todo.due, today)

        if overdue:
            tags.append("overdue")
        elif todo.priority:
            tags.append(f"p{todo.priority}")

        if todo.priority == 3 and "overdue" in tags:
            tags.append("p3")

        return tuple(tags)

    def update_filters(self):
        counts = self.manager.counts()

        numbers = {
            "active": counts["active"],
            "all": counts["active"] + counts["done"],
            "done": counts["done"],
        }

        for key, (button, title) in self.mode_buttons.items():
            button.config(text=f"{title}  {numbers[key]}")

    def update_empty_state(self, mode: str, has_items: bool):
        if has_items:
            self.empty_label.place_forget()
            return

        if self.search.value() or self.current_tag():
            text = "Nothing matches the filter"
        elif mode == "done":
            text = "Nothing finished yet"
        elif self.manager.todos and mode == "active":
            text = "All done ✓\nType above to add more"
        else:
            text = "No todos yet\nType above and press Enter"

        self.empty_label.config(text=text)
        self.empty_label.place(relx=0.5, rely=0.35, anchor="center")

    def update_footer(self):
        counts = self.manager.counts()

        self.undo_button.config(state="normal" if self.manager.can_undo else "disabled")

        if self._flash_job is None:
            self.status.config(
                text=f"{counts['active']} active  ·  {counts['done']} done"
            )

    def flash(self, text: str):
        """A short message in the footer."""
        if self._flash_job is not None:
            self.window.after_cancel(self._flash_job)

        self.status.config(text=text)

        def restore():
            self._flash_job = None
            self.update_footer()

        self._flash_job = self.window.after(2200, restore)

    # =========================================================
    # ADD
    # =========================================================

    def add_lines(self, lines: list[str]):
        created = self.manager.add_many(lines)

        if not created:
            return

        self.entry.clear()
        self.entry.prepare()

        if self.mode.get() == "done":
            self.set_mode("active")

        first = created[0].id

        if self.tree.exists(first):
            self.tree.selection_set([todo.id for todo in created if self.tree.exists(todo.id)])
            self.tree.see(first)

        self.flash("Added 1 todo" if len(created) == 1 else f"Added {len(created)} todos")

    def add_from_entry(self, event=None):
        self.add_lines(self.entry.value().splitlines())

        return "break"

    def on_paste(self, event=None):
        lines = read_clipboard_lines(self.entry)

        if len(lines) > 1:
            self.add_lines(lines)

            return "break"

        # an ordinary single-line paste
        if self.entry.selection_present():
            self.entry.delete("sel.first", "sel.last")

        self.entry.prepare()

        if lines:
            self.entry.insert("insert", lines[0].strip())

        return "break"

    # =========================================================
    # CLICKS AND KEYS
    # =========================================================

    def on_click(self, event):
        row = self.tree.identify_row(event.y)

        if row and self.tree.identify_column(event.x) == "#0":
            self.toggle_ids([row])

            return "break"

        return None

    def on_double_click(self, event):
        row = self.tree.identify_row(event.y)

        if row and self.tree.identify_column(event.x) != "#0":
            self.tree.selection_set([row])
            self.edit_selected()

            return "break"

        return None

    def on_right_click(self, event):
        row = self.tree.identify_row(event.y)

        if not row:
            return

        if row not in self.tree.selection():
            self.tree.selection_set([row])

        self.menu.tk_popup(event.x_root, event.y_root)

    def on_list_key(self, event):
        char = event.char

        if not char or not char.isprintable() or char == " ":
            return None

        if event.state & 0x4 or event.state & 0x20000:      # Ctrl or Alt
            return None

        self.entry.prepare()
        self.entry.insert("end", char)

        return "break"

    def focus_list(self, event=None):
        children = self.tree.get_children()

        if not children:
            return "break"

        if not self.tree.selection():
            self.tree.selection_set(children[0])

        self.tree.focus(self.tree.selection()[0])
        self.tree.focus_set()

        return "break"

    def on_entry_escape(self, event=None):
        if self.entry.value():
            self.entry.clear()
            self.entry.prepare()
        else:
            self.close()

        return "break"

    def on_search_escape(self, event=None):
        if self.search.value():
            self.search.clear()
            self.search.prepare()
            self.refresh()
        else:
            self.entry.prepare()

        return "break"

    def set_mode(self, mode: str):
        self.mode.set(mode)
        self.refresh()

        return "break"

    # =========================================================
    # ACTIONS ON THE SELECTION
    # =========================================================

    def selected_ids(self) -> list[str]:
        return list(self.tree.selection())

    def toggle_selected(self):
        self.toggle_ids(self.selected_ids())

    def toggle_ids(self, ids: list[str]):
        if not ids:
            return

        finishing = any(
            todo is not None and not todo.done
            for todo in (self.manager.get(i) for i in ids)
        )

        self.manager.toggle(ids)

        # in the "Active" view a finished todo disappears: say what happened
        if finishing and self.mode.get() == "active":
            self.flash("Done  ·  Ctrl+Z to undo")

    def delete_selected(self):
        ids = self.selected_ids()

        if not ids:
            return

        # the row that will be selected next
        children = list(self.tree.get_children())
        index = max(children.index(iid) for iid in ids if iid in children)
        following = [iid for iid in children[index + 1:] if iid not in ids]
        before = [iid for iid in children[:index] if iid not in ids]

        self.manager.delete(ids)

        target = (following or before or [None])[0]

        if target and self.tree.exists(target):
            self.tree.selection_set([target])
            self.tree.focus(target)

        self.flash(f"Deleted {len(ids)}  ·  Ctrl+Z to undo")

    def set_priority(self, level: int):
        ids = self.selected_ids()

        if ids:
            self.manager.set_priority(ids, level)

    def set_due(self, days: int | None):
        ids = self.selected_ids()

        if ids:
            self.manager.set_due(
                ids,
                None if days is None else date.today() + timedelta(days=days),
            )

    def clear_done(self):
        count = self.manager.clear_done()

        if count:
            self.flash(f"Removed {count} done  ·  Ctrl+Z to undo")

    def undo(self):
        if self.manager.undo():
            self.flash("Undone")

        return "break"

    # =========================================================
    # EDIT IN PLACE
    # =========================================================

    def edit_selected(self):
        selection = self.tree.selection()

        if not selection:
            return

        iid = selection[0]
        todo = self.manager.get(iid)

        if todo is None:
            return

        self.tree.see(iid)
        self.tree.update_idletasks()

        bbox = self.tree.bbox(iid, "text")

        if not bbox:
            return

        x, y, _, height = bbox

        if self._editor is not None:
            self._editor.destroy()

        editor = tk.Entry(self.tree, font=self.font, relief="solid", bd=1)
        self._editor = editor

        editor.insert(0, todo.raw())
        editor.select_range(0, "end")
        editor.icursor("end")
        editor.place(x=x - 2, y=y, width=self.tree.winfo_width() - x, height=height)
        editor.focus_set()

        finished = {"value": False}

        def finish(commit: bool):
            if finished["value"]:
                return

            finished["value"] = True

            value = editor.get()

            editor.destroy()
            self._editor = None

            self.tree.focus_set()

            if commit and not self.manager.update(iid, value):
                self.flash("The text cannot be empty")

        editor.bind("<Return>", lambda event: finish(True))
        editor.bind("<Escape>", lambda event: finish(False))
        editor.bind("<FocusOut>", lambda event: finish(True))


# ---------------------------------------------------------
# entry point
# ---------------------------------------------------------

def open_todo(root: tk.Misc, manager: TodoManager) -> TodoWindow:
    """Opens the list (or raises the one that is already open)."""
    global _window

    if _window is not None and _window.window.winfo_exists():
        bring_to_front(_window.window)
        _window.entry.prepare()

        return _window

    _window = TodoWindow(root, manager)

    bring_to_front(_window.window)

    return _window
