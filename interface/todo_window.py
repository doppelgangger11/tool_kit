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

The list is a table like in a file manager:
    drag a column border     resize it (that column stops fitting its content)
    double click a border    fit the column to its content again
    click a header           sort; click again to reverse; a third click removes the sorting
    right click a header     show / hide columns, fit all, reset
    the width, columns, sorting and window size are remembered
"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from datetime import date, timedelta
from tkinter import ttk

from scripts.todo_manager import (
    ALL_COLUMNS,
    COLUMN_TITLES,
    DESC_FIRST,
    MAX_COLUMN_WIDTH,
    MIN_COLUMN_WIDTH,
    TodoManager,
    TodoView,
    format_due,
    format_stamp,
    sort_todos,
)

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

CHECK_COLUMN = "#0"

DEFAULT_SIZE = (820, 640)
MIN_SIZE = (560, 340)

COLUMN_ANCHOR = {
    "priority": "center",
}

# the widest an automatic column gets (a pathological tag must not eat the screen);
# anything wider than the window is reached with the horizontal scroll bar
AUTO_FIT_MAX = 700

TEXT_MIN = 140


def due_label(todo, today: date) -> str:
    label, overdue = format_due(todo.due, today)

    if overdue and not todo.done:
        return f"⚠ {label}"

    return label


class TodoWindow:

    def __init__(self, root: tk.Misc, manager: TodoManager):
        self.root = root
        self.manager = manager

        self.view = TodoView(manager.path.with_name("todo_view.json"))

        self.window = tk.Toplevel(root)
        self.window.title("Todo")

        width, height = self.view.size or DEFAULT_SIZE

        self.window.geometry(f"{width}x{height}")
        self.window.minsize(*MIN_SIZE)

        self._flash_job = None
        self._editor = None
        self._resizing = None           # (column, width before the drag)
        self._menu_vars = []            # keeps the header menu variables alive

        self.mode = tk.StringVar(value="active")

        self._build_styles()
        self._build_ui()
        self._bind_keys()

        self.manager.subscribe(self.refresh)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        # real widget sizes are needed to fit the columns
        self.window.update_idletasks()

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
        self.font_head = tkfont.Font(family="Segoe UI", size=10)

        style.configure("Todo.Treeview", rowheight=32, font=self.font, borderwidth=0)
        style.configure("Todo.Treeview.Heading", font=self.font_head, padding=(6, 5))

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

        # ----- footer (packed before the table so a small window never hides it) -----

        footer = tk.Frame(window, padx=14)
        footer.pack(side="bottom", fill="x", pady=(0, 12))

        self.status = tk.Label(footer, text="", fg=GRAY, anchor="w", font=("Segoe UI", 9))
        self.status.pack(side="left", fill="x", expand=True)

        ttk.Button(footer, text="Clear done", command=self.clear_done).pack(side="right")
        self.undo_button = ttk.Button(footer, text="Undo", command=self.undo)
        self.undo_button.pack(side="right", padx=(0, 6))

        # ----- table -----

        body = tk.Frame(window, padx=14, pady=8)
        body.pack(fill="both", expand=True)

        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            body,
            style="Todo.Treeview",
            columns=ALL_COLUMNS,
            displaycolumns=self.view.columns,
            show="tree headings",
            selectmode="extended",
            height=5,
        )

        self.vscroll = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.hscroll = ttk.Scrollbar(body, orient="horizontal", command=self.tree.xview)

        self.tree.configure(
            yscrollcommand=lambda lo, hi: self._set_scroll(self.vscroll, lo, hi),
            xscrollcommand=lambda lo, hi: self._set_scroll(self.hscroll, lo, hi),
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vscroll.grid(row=0, column=1, sticky="ns")
        self.hscroll.grid(row=1, column=0, sticky="ew")

        self._build_columns()

        self.tree.tag_configure("done", foreground="#a0a0a0", font=self.font_done)
        self.tree.tag_configure("overdue", foreground=OVERDUE)

        for level, color in PRIORITY_COLORS.items():
            self.tree.tag_configure(f"p{level}", foreground=color)

        self.tree.tag_configure("p3", font=self.font_bold)

        self.empty_label = tk.Label(
            self.tree, text="", fg=GRAY, font=("Segoe UI", 11), justify="center"
        )

        self.menu = self._build_menu()

    def _build_columns(self):
        tree = self.tree

        tree.column(CHECK_COLUMN, width=44, minwidth=44, stretch=False, anchor="center")

        for column in ALL_COLUMNS:
            tree.column(
                column,
                width=self.view.widths[column],
                minwidth=140 if column == "text" else MIN_COLUMN_WIDTH,
                stretch=(column == "text"),
                anchor=COLUMN_ANCHOR.get(column, "w"),
            )

        self.update_headings()

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

        # table
        tree = self.tree

        tree.bind("<Button-1>", self.on_click)
        tree.bind("<ButtonRelease-1>", self.on_release)
        tree.bind("<Double-1>", self.on_double_click)
        tree.bind("<Button-3>", self.on_right_click)
        tree.bind("<<TreeviewSelect>>", lambda event: self.update_footer())
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

    @staticmethod
    def _set_scroll(scrollbar, low, high):
        """A scroll bar that is only visible when there is something to scroll."""
        scrollbar.set(low, high)

        if float(low) <= 0.0 and float(high) >= 1.0:
            scrollbar.grid_remove()
        else:
            scrollbar.grid()

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

        self.remember_widths()
        self.view.size = (self.window.winfo_width(), self.window.winfo_height())
        self.view.save()

        _window = None
        self.window.destroy()

    # =========================================================
    # COLUMNS: headings, sorting, widths
    # =========================================================

    def heading_text(self, key: str, title: str) -> str:
        sort = self.view.sort

        if sort and sort[0] == key:
            return f"{title} {'▼' if sort[1] else '▲'}"

        return title

    def update_headings(self):
        tree = self.tree

        tree.heading(
            CHECK_COLUMN,
            text=self.heading_text("done", "✓"),
            anchor="center",
            command=lambda: self.on_header_click("done"),
        )

        for column in ALL_COLUMNS:
            tree.heading(
                column,
                text=self.heading_text(column, COLUMN_TITLES[column]),
                anchor=COLUMN_ANCHOR.get(column, "w"),
                command=lambda column=column: self.on_header_click(column),
            )

    def on_header_click(self, key: str):
        """First click sorts, the second reverses, the third removes the sorting."""
        current = self.view.sort
        first = key in DESC_FIRST

        if current is None or current[0] != key:
            new = (key, first)
        elif current[1] == first:
            new = (key, not first)
        else:
            new = None

        self.set_sort(new)

    def set_sort(self, sort):
        self.view.sort = sort
        self.view.save()

        self.update_headings()
        self.refresh()

    def content_width(self, column: str) -> int:
        """Width that shows the header and the longest value of the column."""
        heading = self.font_head.measure(COLUMN_TITLES[column]) + 32    # room for the arrow

        # measured with the bold font: rows with the highest priority are bold
        cells = max(
            (
                self.font_bold.measure(self.tree.set(iid, column))
                for iid in self.tree.get_children()
            ),
            default=0,
        ) + 20

        return max(MIN_COLUMN_WIDTH, min(max(heading, cells), AUTO_FIT_MAX, MAX_COLUMN_WIDTH))

    def fit_column(self, column: str):
        width = self.content_width(column)

        self.tree.column(column, width=width)
        self.view.widths[column] = width

    def fit_auto_columns(self):
        """
        Columns that were not resized by hand always show their whole content;
        the Task column takes the space that is left.
        """
        for column in self.view.columns:
            if column != "text" and column not in self.view.manual:
                self.fit_column(column)

        self.balance_text_column()

    def balance_text_column(self):
        if "text" in self.view.manual:
            return

        others = 44 + sum(
            int(self.tree.column(column, "width"))
            for column in self.view.columns
            if column != "text"
        )

        width = max(TEXT_MIN, self.tree.winfo_width() - others)

        self.tree.column("text", width=width)
        self.view.widths["text"] = width

    def fit_all(self):
        self.view.manual = set()

        self.fit_auto_columns()
        self.view.save()

    def reset_columns(self):
        self.view.reset_columns()

        self.tree.configure(displaycolumns=self.view.columns)

        for column in ALL_COLUMNS:
            self.tree.column(column, width=self.view.widths[column])

        self.fit_auto_columns()
        self.view.save()

    def remember_widths(self):
        for column in ALL_COLUMNS:
            try:
                self.view.widths[column] = int(self.tree.column(column, "width"))
            except (tk.TclError, ValueError):
                pass

    def set_column_visible(self, column: str, visible: bool):
        wanted = set(self.view.columns)

        if visible:
            wanted.add(column)
        else:
            wanted.discard(column)

        wanted.add("text")

        self.view.columns = [name for name in ALL_COLUMNS if name in wanted]

        self.tree.configure(displaycolumns=self.view.columns)

        self.fit_auto_columns()
        self.view.save()

    def separator_column(self, x: int) -> str | None:
        """
        The column whose right border is under x (the header borders you drag).
        """
        tree = self.tree

        order = [CHECK_COLUMN] + list(self.view.columns)

        widths = [int(tree.column(column, "width")) for column in order]
        offset = int(tree.xview()[0] * sum(widths))

        edge = 0
        best = None

        for column, width in zip(order, widths):
            edge += width

            distance = abs(edge - offset - x)

            if distance <= 6 and (best is None or distance < best[0]):
                best = (distance, column)

        return best[1] if best else None

    def show_header_menu(self, event):
        menu = tk.Menu(self.window, tearoff=False)

        self._menu_vars = []

        for column in ALL_COLUMNS:
            if column == "text":
                continue

            variable = tk.BooleanVar(value=column in self.view.columns)
            self._menu_vars.append(variable)

            menu.add_checkbutton(
                label=COLUMN_TITLES[column],
                variable=variable,
                command=lambda column=column, variable=variable:
                    self.set_column_visible(column, variable.get()),
            )

        menu.add_separator()
        menu.add_command(label="Fit columns to content", command=self.fit_all)
        menu.add_command(label="Reset columns", command=self.reset_columns)
        menu.add_command(
            label="Reset sorting",
            command=lambda: self.set_sort(None),
            state="normal" if self.view.sort else "disabled",
        )

        menu.tk_popup(event.x_root, event.y_root)

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

        if self.view.sort:
            items = sort_todos(items, *self.view.sort)

        selected = set(self.tree.selection())
        top = self.tree.yview()[0]

        self.tree.delete(*self.tree.get_children())

        today = date.today()

        for todo in items:
            self.tree.insert(
                "",
                "end",
                iid=todo.id,
                text=CHECK_ON if todo.done else CHECK_OFF,
                values=(
                    todo.text,
                    "!" * todo.priority,
                    due_label(todo, today),
                    " ".join(f"#{tag}" for tag in todo.tags),
                    format_stamp(todo.created, today),
                    format_stamp(todo.done_at, today),
                ),
                tags=self.row_tags(todo, today),
            )

        self.fit_auto_columns()

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

        if self._flash_job is not None:
            return

        selection = self.tree.selection()
        todo = self.manager.get(selection[0]) if len(selection) == 1 else None

        if todo is not None:
            # the whole todo, even when the table cuts it
            text = todo.raw()

            if len(text) > 110:
                text = text[:109] + "…"

            self.status.config(text=text)
        else:
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
        region = self.tree.identify_region(event.x, event.y)

        # the start of a column border drag: remember what is being resized
        if region == "separator":
            column = self.separator_column(event.x)

            if column and column != CHECK_COLUMN:
                self._resizing = (column, int(self.tree.column(column, "width")))
            else:
                self._resizing = None

            return None

        self._resizing = None

        row = self.tree.identify_row(event.y)

        if row and self.tree.identify_column(event.x) == "#0":
            self.toggle_ids([row])

            return "break"

        return None

    def on_release(self, event):
        if self._resizing is None:
            return

        column, before = self._resizing
        self._resizing = None

        after = int(self.tree.column(column, "width"))

        # a width set by hand is kept; the column stops fitting its content
        if after != before:
            self.view.manual.add(column)
            self.view.widths[column] = after
            self.view.save()

    def on_double_click(self, event):
        region = self.tree.identify_region(event.x, event.y)

        # a double click on a column border fits the column to its content
        if region == "separator":
            column = self.separator_column(event.x)

            if column and column != CHECK_COLUMN:
                self.view.manual.discard(column)

                if column == "text":
                    self.balance_text_column()
                else:
                    self.fit_column(column)
                    self.balance_text_column()

                self.view.save()

            return "break"

        row = self.tree.identify_row(event.y)

        if row and self.tree.identify_column(event.x) != "#0":
            self.tree.selection_set([row])
            self.edit_selected()

            return "break"

        return None

    def on_right_click(self, event):
        if self.tree.identify_region(event.x, event.y) in ("heading", "separator"):
            self.show_header_menu(event)

            return

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
        editor.place(
            x=x - 2,
            y=y,
            width=max(160, self.tree.winfo_width() - x - 4),
            height=height,
        )
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
