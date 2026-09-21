import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from scripts.note_manager import NotesManager, Note

class NoteEditor(tk.Toplevel):

    def __init__(self, parent, notes_window, note=None):
        super().__init__(parent)

        self.notes_window = notes_window
        self.note = note

        self.title("New note" if note is None else "Edit note")
        self.geometry("700x600")
        self.minsize(500, 400)

        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self._load_note()
        self._setup_shortcuts()

        self.protocol("WM_DELETE_WINDOW", self._close)

    def _create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # =========================
        # Theme
        # =========================

        theme_frame = ttk.Frame(self)
        theme_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=10,
            pady=(10, 5)
        )

        theme_frame.columnconfigure(1, weight=1)

        ttk.Label(
            theme_frame,
            text="Theme:"
        ).grid(
            row=0,
            column=0,
            padx=(0, 10)
        )

        self.theme_entry = ttk.Entry(theme_frame)
        self.theme_entry.grid(
            row=0,
            column=1,
            sticky="ew"
        )

        # =========================
        # Date
        # =========================

        date_frame = ttk.Frame(self)
        date_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=10,
            pady=5
        )

        ttk.Label(
            date_frame,
            text="Date:"
        ).grid(
            row=0,
            column=0,
            padx=(0, 10)
        )

        self.date_label = ttk.Label(date_frame)
        self.date_label.grid(
            row=0,
            column=1,
            sticky="w"
        )

        # =========================
        # Text editor
        # =========================

        text_frame = ttk.Frame(self)
        text_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=10,
            pady=5
        )

        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        self.text = tk.Text(
            text_frame,
            wrap="word",
            undo=True
        )

        self.text.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        scrollbar = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=self.text.yview
        )

        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        self.text.configure(
            yscrollcommand=scrollbar.set
        )

        # =========================
        # Buttons
        # =========================

        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=10,
            pady=10
        )

        ttk.Button(
            buttons_frame,
            text="Cancel",
            command=self._close
        ).pack(
            side="right",
            padx=(5, 0)
        )

        ttk.Button(
            buttons_frame,
            text="Save",
            command=self._save
        ).pack(
            side="right"
        )

    def _load_note(self):
        if self.note is None:
            now = datetime.now().replace(microsecond=0)

            self.date_label.config(
                text=now.strftime("%Y-%m-%d %H:%M:%S")
            )

            self.theme_entry.focus_set()

            return

        self.theme_entry.insert(
            0,
            self.note.theme
        )

        self.date_label.config(
            text=self.note.date.strftime("%Y-%m-%d %H:%M:%S")
        )

        self.text.insert(
            "1.0",
            self.note.note
        )

        self.text.focus_set()

    # ==========================================================
    # Shortcuts
    # ==========================================================

    def _setup_shortcuts(self):
        for widget in (self.theme_entry, self.text):
            widget.bind("<Control-KeyPress>", self._handle_shortcut)


    def _handle_shortcut(self, event):
        shortcuts = {
            65: self._select_all,  # A
            67: self._copy,        # C
            86: self._paste,       # V
            88: self._cut,         # X
            90: self._undo,        # Z
            89: self._redo,        # Y
            83: self._save,        # S
        }

        command = shortcuts.get(event.keycode)

        if command is not None:
            command()
            return "break"

    def _copy(self, event=None):
        self.text.event_generate("<<Copy>>")
        return "break"

    def _paste(self, event=None):
        self.text.event_generate("<<Paste>>")
        return "break"

    def _cut(self, event=None):
        self.text.event_generate("<<Cut>>")
        return "break"

    def _select_all(self, event=None):
        self.text.tag_add(
            "sel",
            "1.0",
            "end"
        )

        self.text.mark_set(
            "insert",
            "1.0"
        )

        self.text.see("insert")

        return "break"

    def _undo(self, event=None):
        try:
            self.text.edit_undo()
        except tk.TclError:
            pass

        return "break"

    def _redo(self, event=None):
        try:
            self.text.edit_redo()
        except tk.TclError:
            pass

        return "break"

    # ==========================================================
    # Save / Close
    # ==========================================================

    def _save(self, event=None):
        theme = self.theme_entry.get().strip()
        text = self.text.get("1.0", "end-1c")

        if not theme:
            messagebox.showwarning(
                "Empty theme",
                "Theme cannot be empty.",
                parent=self
            )

            self.theme_entry.focus_set()

            return "break"

        if self.note is not None:
            self.note.theme = theme
            self.note.note = text

        else:
            self.notes_window.notes_manager.create_note(
                theme=theme,
                note=text
            )

        self.notes_window.notes_manager.write_notes()
        self.notes_window.refresh()

        self._close()

        return "break"

    def _close(self):
        self.grab_release()
        self.destroy()
        
        
class NotesWindow(tk.Toplevel):
    def __init__(self, parent, notes_manager: NotesManager):
        super().__init__(parent)
        self.notes_manager = notes_manager
        self.title("Notes")
        self.geometry("700x600")
        self.minsize(500, 400)
        self._create_widgets()
        self.refresh()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top_frame = ttk.Frame(self)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ttk.Button(top_frame, text="+ New note", command=self.new_note).pack(side="left")
        ttk.Button(top_frame, text="↻ Refresh", command=self.refresh).pack(side="left", padx=5)

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

        self.notes_frame.bind("<Configure>", self._update_scrollregion)
        self.canvas.bind("<Configure>", self._resize_inner_frame)
        self.canvas.bind("<Enter>", self._enable_mousewheel)
        self.canvas.bind("<Leave>", self._disable_mousewheel)

    def _enable_mousewheel(self, event=None):
        self.canvas.bind_all("<MouseWheel>", self._mousewheel)

    def _disable_mousewheel(self, event=None):
        self.canvas.unbind_all("<MouseWheel>")
    
    def _update_scrollregion(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_inner_frame(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def refresh(self):
        for widget in self.notes_frame.winfo_children():
            widget.destroy()

        notes = sorted(self.notes_manager.notes, key=lambda note: note.date, reverse=True)

        if not notes:
            ttk.Label(self.notes_frame, text="No notes yet.").pack(pady=30)
            return

        for note in notes:
            self._create_note_widget(note)

        self._update_scrollregion()

    def _create_note_widget(self, note):
        frame = ttk.Frame(self.notes_frame, relief="ridge", borderwidth=1)
        frame.pack(fill="x", pady=4)
        frame.columnconfigure(0, weight=1)

        info_frame = ttk.Frame(frame)
        info_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        info_frame.columnconfigure(0, weight=1)

        theme_label = ttk.Label(info_frame, text=note.theme, font=("TkDefaultFont", 11, "bold"))
        theme_label.grid(row=0, column=0, sticky="w")

        date_label = ttk.Label(info_frame, text=note.date.strftime("%Y-%m-%d %H:%M:%S"))
        date_label.grid(row=1, column=0, sticky="w")

        preview = note.note.replace("\n", " ")
        if len(preview) > 100:
            preview = preview[:100] + "..."

        preview_label = ttk.Label(info_frame, text=preview)
        preview_label.grid(row=2, column=0, sticky="w", pady=(5, 0))

        buttons_frame = ttk.Frame(frame)
        buttons_frame.grid(row=0, column=1, sticky="ns", padx=10)

        ttk.Button(buttons_frame, text="✍", width=3, command=lambda n=note: self.edit_note(n)).pack(side="left", padx=2)
        ttk.Button(buttons_frame, text="🗑", width=3, command=lambda n=note: self.delete_note(n)).pack(side="left", padx=2)

        for widget in (frame, info_frame, theme_label, date_label, preview_label):
            widget.bind("<Button-1>", lambda event, n=note: self.edit_note(n))

    def new_note(self):
        NoteEditor(self, self)

    def edit_note(self, note):
        NoteEditor(self, self, note)

    def delete_note(self, note):
        result = messagebox.askyesno("Delete note", f'Delete "{note.theme}"?', parent=self)
        if not result:
            return

        self.notes_manager.delete(note.id)
        self.notes_manager.write_notes()
        self.refresh()

    def _close(self):
        self.canvas.unbind_all("<MouseWheel>")
        self.destroy()
 
        
notes_window = None

def open_notes(root, notes_manager):
    global notes_window

    if notes_window is not None and notes_window.winfo_exists():
        notes_window.lift()
        notes_window.focus_force()
        return

    notes_window = NotesWindow(root, notes_manager)
