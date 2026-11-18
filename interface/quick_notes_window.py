import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path
import re

from scripts.note_store import NoteStore, Note
from scripts.mdcells import split_cells, join_cells, is_open_fence, next_prefix, TASK_RE


class CellBlock(ttk.Frame):
    """Один редактируемый или отрендеренный Markdown-блок (ячейка)."""
    def __init__(self, parent, editor, text="", active=False):
        super().__init__(parent)
        self.editor = editor
        self.raw_text = text
        self.is_active = active

        self.columnconfigure(0, weight=1)
        self._build_ui()

    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        if self.is_active:
            self._build_editor()
        else:
            self._build_preview()

    def _build_editor(self):
        lines = max(1, self.raw_text.count("\n") + 1)
        self.text_widget = tk.Text(
            self,
            height=lines,
            wrap="word",
            font=("Consolas", 10),
            relief="solid",
            borderwidth=1,
            padx=6,
            pady=4,
            undo=True
        )
        self.text_widget.insert("1.0", self.raw_text)
        self.text_widget.grid(row=0, column=0, sticky="ew", pady=2)

        self.text_widget.bind("<KeyRelease>", self._auto_resize)
        self.text_widget.bind("<Return>", self._on_enter)
        self.text_widget.bind("<Shift-Return>", lambda e: None)  # Обычный перенос строки
        self.text_widget.bind("<BackSpace>", self._on_backspace)
        self.text_widget.bind("<Up>", self._on_up)
        self.text_widget.bind("<Down>", self._on_down)
        self.text_widget.bind("<FocusOut>", self._on_focus_out)
        self.text_widget.bind("<Tab>", self._on_tab)

    def _build_preview(self):
        text = self.raw_text.strip()
        if not text:
            text = " "

        # Проверка на чекбокс-задачу: - [ ] или - [x]
        task_match = TASK_RE.match(text.split("\n", 1)[0])
        if task_match:
            frame = ttk.Frame(self)
            frame.grid(row=0, column=0, sticky="ew", pady=2, padx=4)
            is_checked = task_match.group(3).lower() == "x"
            var = tk.BooleanVar(value=is_checked)

            def toggle_task():
                state = "x" if var.get() else " "
                lines = self.raw_text.split("\n")
                lines[0] = TASK_RE.sub(rf"\1\2 [{state}] \4", lines[0], count=1)
                self.raw_text = "\n".join(lines)
                self._build_ui()
                self.editor.mark_dirty()

            cb = ttk.Checkbutton(frame, variable=var, command=toggle_task)
            cb.pack(side="left", anchor="n")

            lbl_text = task_match.group(4)
            if "\n" in self.raw_text:
                lbl_text += "\n" + self.raw_text.split("\n", 1)[1]

            lbl = ttk.Label(
                frame,
                text=lbl_text,
                font=("TkDefaultFont", 10, "overstrike" if is_checked else "normal"),
                foreground="gray" if is_checked else "black",
                wraplength=600,
                justify="left"
            )
            lbl.pack(side="left", fill="x", expand=True, padx=(4, 0))
            lbl.bind("<Button-1>", lambda e: self.editor.activate_cell(self))
            frame.bind("<Button-1>", lambda e: self.editor.activate_cell(self))
            return

        # Заголовки (# ... ######)
        heading_match = re.match(r"^(#{1,6})\s+(.*)$", text)
        if heading_match:
            level = len(heading_match.group(1))
            sizes = {1: 16, 2: 14, 3: 12, 4: 11, 5: 10, 6: 10}
            lbl = ttk.Label(
                self,
                text=heading_match.group(2),
                font=("TkDefaultFont", sizes.get(level, 10), "bold"),
                wraplength=620,
                justify="left"
            )
            lbl.grid(row=0, column=0, sticky="ew", pady=(6, 2), padx=4)
            lbl.bind("<Button-1>", lambda e: self.editor.activate_cell(self))
            return

        # Горизонтальная линия (---, ***)
        if re.match(r"^\s*([-*_])(\s*\1){2,}\s*$", text):
            sep = ttk.Separator(self, orient="horizontal")
            sep.grid(row=0, column=0, sticky="ew", pady=8, padx=4)
            sep.bind("<Button-1>", lambda e: self.editor.activate_cell(self))
            return

        # Блок кода (``` ... ```)
        if text.startswith(("```", "~~~")):
            lines = text.split("\n")
            code_body = "\n".join(lines[1:-1] if len(lines) > 1 and lines[-1].startswith(("```", "~~~")) else lines[1:])
            lbl = tk.Label(
                self,
                text=code_body or " ",
                font=("Consolas", 9),
                bg="#f4f4f4",
                fg="#222222",
                anchor="w",
                justify="left",
                padx=8,
                pady=6,
                relief="groove",
                borderwidth=1
            )
            lbl.grid(row=0, column=0, sticky="ew", pady=3, padx=4)
            lbl.bind("<Button-1>", lambda e: self.editor.activate_cell(self))
            return

        # Цитата (> ...)
        if text.startswith(">"):
            quote_text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
            lbl = tk.Label(
                self,
                text=quote_text,
                font=("TkDefaultFont", 10, "italic"),
                fg="#555555",
                bg="#f9f9f9",
                anchor="w",
                justify="left",
                padx=10,
                pady=4,
                wraplength=600
            )
            lbl.grid(row=0, column=0, sticky="ew", pady=2, padx=(10, 4))
            lbl.bind("<Button-1>", lambda e: self.editor.activate_cell(self))
            return

        # Обычный текст или элемент списка
        display_text = re.sub(r"^(\s*)[-*+]\s+", r"\1• ", text)
        lbl = ttk.Label(
            self,
            text=display_text,
            font=("TkDefaultFont", 10),
            wraplength=620,
            justify="left"
        )
        lbl.grid(row=0, column=0, sticky="ew", pady=2, padx=4)
        lbl.bind("<Button-1>", lambda e: self.editor.activate_cell(self))

    def sync_from_widget(self):
        if self.is_active and hasattr(self, "text_widget"):
            self.raw_text = self.text_widget.get("1.0", "end-1c")

    def set_active(self, active: bool, cursor_pos="end"):
        if self.is_active == active:
            if active and hasattr(self, "text_widget"):
                self.text_widget.focus_set()
                self.text_widget.mark_set("insert", cursor_pos)
            return
        self.sync_from_widget()
        self.is_active = active
        self._build_ui()
        if active and hasattr(self, "text_widget"):
            self.text_widget.focus_set()
            self.text_widget.mark_set("insert", cursor_pos)
            self._auto_resize()

    def _auto_resize(self, event=None):
        if hasattr(self, "text_widget"):
            content = self.text_widget.get("1.0", "end-1c")
            lines = max(1, content.count("\n") + 1)
            self.text_widget.configure(height=lines)

    def _on_focus_out(self, event):
        self.sync_from_widget()
        self.editor.mark_dirty()

    def _on_enter(self, event):
        self.sync_from_widget()
        # Если открыт блок кода ``` или нажат Shift — перенос внутри ячейки
        if is_open_fence(self.raw_text):
            return None

        cursor = self.text_widget.index("insert")
        before = self.text_widget.get("1.0", cursor)
        after = self.text_widget.get(cursor, "end-1c")

        prefix = next_prefix(before)
        if prefix == "":
            # Пустой элемент списка -> выходим из списка (очищаем маркер)
            self.raw_text = ""
            self._build_ui()
            self.text_widget.focus_set()
            return "break"

        self.raw_text = before
        self._build_ui()
        new_text = (prefix or "") + after.lstrip("\n")
        self.editor.insert_cell_after(self, new_text, cursor_pos=f"1.{len(prefix or '')}")
        return "break"

    def _on_backspace(self, event):
        if self.text_widget.index("insert") == "1.0" and not self.text_widget.tag_ranges("sel"):
            self.sync_from_widget()
            self.editor.merge_with_previous(self)
            return "break"
        return None

    def _on_up(self, event):
        line = int(self.text_widget.index("insert").split(".")[0])
        if line == 1:
            self.editor.focus_adjacent(self, -1)
            return "break"
        return None

    def _on_down(self, event):
        line = int(self.text_widget.index("insert").split(".")[0])
        last_line = int(self.text_widget.index("end-1c").split(".")[0])
        if line == last_line:
            self.editor.focus_adjacent(self, 1)
            return "break"
        return None

    def _on_tab(self, event):
        if event.state & 0x0001:  # Shift+Tab
            content = self.text_widget.get("1.0", "1.4")
            spaces = len(content) - len(content.lstrip(" "))
            if spaces:
                self.text_widget.delete("1.0", f"1.{spaces}")
        else:
            self.text_widget.insert("1.0", "    ")
        return "break"


class NoteEditor(tk.Toplevel):
    def __init__(self, parent, notes_window, note: Note | None = None):
        super().__init__(parent)
        self.notes_window = notes_window
        self.store: NoteStore = notes_window.store
        self.note = note
        self.cells: list[CellBlock] = []
        self.dirty = False

        self.title("New note" if note is None else f"Edit: {note.display_title}")
        self.geometry("720x620")
        self.minsize(520, 420)
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self._load_note()
        self._setup_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # Title
        title_frame = ttk.Frame(self)
        title_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        title_frame.columnconfigure(1, weight=1)

        ttk.Label(title_frame, text="Title:").grid(row=0, column=0, padx=(0, 8))
        self.title_entry = ttk.Entry(title_frame, font=("TkDefaultFont", 11, "bold"))
        self.title_entry.grid(row=0, column=1, sticky="ew")

        # Meta info (Created & file path)
        meta_frame = ttk.Frame(self)
        meta_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=2)
        self.meta_label = ttk.Label(meta_frame, foreground="gray")
        self.meta_label.pack(side="left")

        self.mode_btn = ttk.Button(meta_frame, text="Raw Markdown", command=self._toggle_raw_mode)
        self.mode_btn.pack(side="right")

        # Scrollable Cells Area
        container = ttk.Frame(self, relief="sunken", borderwidth=1)
        container.grid(row=2, column=0, sticky="nsew", padx=12, pady=6)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(container, bg="white", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.cells_frame = tk.Frame(self.canvas, bg="white")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.cells_frame, anchor="nw")

        self.cells_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.canvas_window, width=e.width))
        # Клик по пустому месту ниже ячеек активирует последнюю ячейку или создает новую
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # Raw text fallback widget (hidden by default)
        self.raw_mode = False
        self.raw_text = tk.Text(container, wrap="word", font=("Consolas", 10), undo=True)

        # Bottom bar
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=10)

        ttk.Label(
            btn_frame,
            text="Enter: new cell | Shift+Enter: new line | Ctrl+S: save",
            foreground="gray"
        ).pack(side="left")

        ttk.Button(btn_frame, text="Cancel", command=self._close).pack(side="right", padx=(6, 0))
        ttk.Button(btn_frame, text="Save", command=self._save).pack(side="right")

    def _load_note(self):
        if self.note is None:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.meta_label.config(text=f"Created: {now}  |  New .md file")
            self._render_cells([""], active_idx=0)
            self.title_entry.focus_set()
            return

        # Перечитываем с диска на случай внешних правок (Obsidian / VS Code)
        fresh = self.store.reload(self.note)
        if fresh:
            self.note = fresh

        self.title_entry.insert(0, self.note.title)
        self.meta_label.config(text=f"Created: {self.note.created}  |  File: {self.note.id}.md")

        parsed_cells = split_cells(self.note.body)
        if not parsed_cells:
            parsed_cells = [""]
        self._render_cells(parsed_cells, active_idx=None)

    def _render_cells(self, cell_texts: list[str], active_idx: int | None = 0):
        for cell in self.cells:
            cell.destroy()
        self.cells.clear()

        for i, txt in enumerate(cell_texts):
            block = CellBlock(self.cells_frame, self, text=txt, active=(i == active_idx))
            block.pack(fill="x", padx=6, pady=1)
            self.cells.append(block)

        if active_idx is not None and 0 <= active_idx < len(self.cells):
            self.cells[active_idx].set_active(True)

    def activate_cell(self, target_cell: CellBlock, cursor_pos="end"):
        for cell in self.cells:
            if cell is not target_cell:
                cell.set_active(False)
        target_cell.set_active(True, cursor_pos=cursor_pos)

    def insert_cell_after(self, current_cell: CellBlock, text: str, cursor_pos="1.0"):
        idx = self.cells.index(current_cell)
        current_cell.set_active(False)
        new_block = CellBlock(self.cells_frame, self, text=text, active=True)
        self.cells.insert(idx + 1, new_block)
        self._repack_cells()
        new_block.set_active(True, cursor_pos=cursor_pos)
        self.mark_dirty()

    def merge_with_previous(self, current_cell: CellBlock):
        idx = self.cells.index(current_cell)
        if idx == 0:
            return
        prev_cell = self.cells[idx - 1]
        prev_len = len(prev_cell.raw_text)
        merged_text = prev_cell.raw_text + current_cell.raw_text

        current_cell.destroy()
        self.cells.pop(idx)
        prev_cell.raw_text = merged_text
        prev_cell.set_active(True, cursor_pos=f"1.0 + {prev_len} chars")
        self.mark_dirty()

    def focus_adjacent(self, current_cell: CellBlock, delta: int):
        idx = self.cells.index(current_cell) + delta
        if 0 <= idx < len(self.cells):
            self.activate_cell(self.cells[idx], cursor_pos="end" if delta < 0 else "1.0")

    def _repack_cells(self):
        for cell in self.cells:
            cell.pack_forget()
            cell.pack(fill="x", padx=6, pady=1)

    def _on_canvas_click(self, event):
        if not self.cells:
            self._render_cells([""], active_idx=0)
            return
        last = self.cells[-1]
        last.sync_from_widget()
        if last.raw_text.strip():
            self.insert_cell_after(last, "")
        else:
            self.activate_cell(last)

    def _toggle_raw_mode(self):
        if not self.raw_mode:
            # Переход из ячеек в сырой Markdown
            md_body = self._collect_markdown()
            self.canvas.grid_remove()
            self.raw_text.delete("1.0", "end")
            self.raw_text.insert("1.0", md_body)
            self.raw_text.grid(row=0, column=0, sticky="nsew")
            self.mode_btn.config(text="Cell View")
            self.raw_mode = True
        else:
            # Переход обратно в ячейки
            md_body = self.raw_text.get("1.0", "end-1c")
            self.raw_text.grid_remove()
            self.canvas.grid(row=0, column=0, sticky="nsew")
            parsed = split_cells(md_body) or [""]
            self._render_cells(parsed, active_idx=0)
            self.mode_btn.config(text="Raw Markdown")
            self.raw_mode = False

    def _collect_markdown(self) -> str:
        if self.raw_mode:
            return self.raw_text.get("1.0", "end-1c")
        for cell in self.cells:
            cell.sync_from_widget()
        return join_cells([c.raw_text for c in self.cells])

    def mark_dirty(self):
        self.dirty = True

    def _setup_shortcuts(self):
        self.bind("<Control-s>", self._save)
        self.bind("<Control-S>", self._save)
        self.bind("<Escape>", self._close)

    def _save(self, event=None):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Empty title", "Title cannot be empty.", parent=self)
            self.title_entry.focus_set()
            return "break"

        body = self._collect_markdown()

        if self.note is None:
            self.store.create(title=title, body=body)
        else:
            self.note.title = title
            self.note.body = body
            self.store.save(self.note)

        self.notes_window.refresh()
        self._close()
        return "break"

    def _close(self, event=None):
        self.grab_release()
        self.destroy()
        return "break"


class NotesWindow(tk.Toplevel):
    def __init__(self, parent, store: NoteStore):
        super().__init__(parent)
        self.store = store
        self.title("Quick Notes (Markdown)")
        self.geometry("720x620")
        self.minsize(520, 420)

        self._create_widgets()
        self._setup_shortcuts()
        self.refresh()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Top panel
        top_frame = ttk.Frame(self)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top_frame.columnconfigure(3, weight=1)

        ttk.Button(top_frame, text="+ New note", command=self.new_note).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(top_frame, text="↻ Refresh", command=self.refresh).grid(row=0, column=1, padx=(0, 10))
        ttk.Label(top_frame, text="Search:").grid(row=0, column=2, sticky="e", padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(top_frame, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=3, sticky="ew")

        ttk.Button(top_frame, text="✕", width=3, command=self._clear_search).grid(row=0, column=4, padx=(5, 0))
        self.search_var.trace_add("write", lambda *_: self.refresh())

        # Notes container
        container = ttk.Frame(self)
        container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(container, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.notes_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.notes_frame, anchor="nw")

        self.notes_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.canvas_window, width=e.width))
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _setup_shortcuts(self):
        self.bind("<Control-f>", lambda e: (self.search_entry.focus_set(), self.search_entry.select_range(0, "end")))
        self.bind("<Escape>", lambda e: self._clear_search())

    def _clear_search(self):
        self.search_var.set("")
        self.search_entry.focus_set()

    def _mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def refresh(self):
        for widget in self.notes_frame.winfo_children():
            widget.destroy()

        # NoteStore.list() сам сканирует .md файлы, фильтрует по query и сортирует (pinned сверху, далее по mtime)
        notes = self.store.list(query=self.search_var.get())

        pinned_notes = [n for n in notes if n.pinned]
        unpinned_notes = [n for n in notes if not n.pinned]

        if pinned_notes:
            self._create_section("📌 Pinned")
            for note in pinned_notes:
                self._create_note_widget(note)

        if unpinned_notes:
            if pinned_notes:
                ttk.Separator(self.notes_frame, orient="horizontal").pack(fill="x", pady=10)
            self._create_section("Notes")
            for note in unpinned_notes:
                self._create_note_widget(note)

        if not notes:
            msg = "No matching notes." if self.search_var.get().strip() else "No notes yet."
            ttk.Label(self.notes_frame, text=msg).pack(pady=30)

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _create_section(self, title):
        ttk.Label(self.notes_frame, text=title, font=("TkDefaultFont", 11, "bold")).pack(fill="x", pady=(8, 4))

    def _create_note_widget(self, note: Note):
        frame = ttk.Frame(self.notes_frame, relief="ridge", borderwidth=1)
        frame.pack(fill="x", pady=4)
        frame.columnconfigure(0, weight=1)

        info_frame = ttk.Frame(frame)
        info_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        info_frame.columnconfigure(0, weight=1)

        title_lbl = ttk.Label(info_frame, text=note.display_title, font=("TkDefaultFont", 11, "bold"))
        title_lbl.grid(row=0, column=0, sticky="w")

        date_lbl = ttk.Label(info_frame, text=note.created, foreground="gray")
        date_lbl.grid(row=1, column=0, sticky="w")

        preview_text = note.preview(limit=100)
        preview_lbl = ttk.Label(info_frame, text=preview_text)
        preview_lbl.grid(row=2, column=0, sticky="w", pady=(4, 0))

        buttons_frame = ttk.Frame(frame)
        buttons_frame.grid(row=0, column=1, sticky="ns", padx=10)

        ttk.Button(
            buttons_frame,
            text="📍" if note.pinned else "📌",
            width=3,
            command=lambda n=note: self.toggle_pin(n)
        ).pack(side="left", padx=2)

        ttk.Button(
            buttons_frame,
            text="🗑",
            width=3,
            command=lambda n=note: self.delete_note(n)
        ).pack(side="left", padx=2)

        for widget in (frame, info_frame, title_lbl, date_lbl, preview_lbl):
            widget.bind("<Button-1>", lambda e, n=note: self.edit_note(n))

    def toggle_pin(self, note: Note):
        note.pinned = not note.pinned
        self.store.save(note)
        self.refresh()

    def new_note(self):
        NoteEditor(self, self)

    def edit_note(self, note: Note):
        NoteEditor(self, self, note)

    def delete_note(self, note: Note):
        if messagebox.askyesno("Delete note", f'Delete "{note.display_title}"?', parent=self):
            self.store.delete(note)
            self.refresh()

    def _close(self):
        self.canvas.unbind_all("<MouseWheel>")
        self.destroy()


notes_window = None


def open_notes(root, notes_store_or_dir):
    global notes_window

    # Поддержка передачи как готового NoteStore, так и пути (str / Path)
    if isinstance(notes_store_or_dir, NoteStore):
        store = notes_store_or_dir
    else:
        store = NoteStore(Path(notes_store_or_dir))

    if notes_window is not None and notes_window.winfo_exists():
        notes_window.lift()
        notes_window.focus_force()
        return

    notes_window = NotesWindow(root, store)
