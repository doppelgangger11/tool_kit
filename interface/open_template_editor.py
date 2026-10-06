import json
import re
import shutil
import tkinter as tk

from pathlib import Path
from tkinter import ttk, messagebox, filedialog


PROJECT_ROOT = "$active_folder$/$name_of_project$"
INVALID_CHARS = '<>:"|?*'


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _dir_value(sub: str) -> str:
    """'' -> $active_folder$/$name_of_project$/ ; 'dags' -> .../dags"""
    return f"{PROJECT_ROOT}/{sub}" if sub else f"{PROJECT_ROOT}/"


def _dir_label(value: str) -> str:
    return value.removeprefix(PROJECT_ROOT).strip("/") or "(project root)"


def _clean_sub(text: str):
    """Возвращает (подпапка, ошибка)."""
    text = text.strip().replace("\\", "/").strip("/")

    if not text:
        return "", None

    for part in text.split("/"):
        if part in ("", ".", ".."):
            return None, "Invalid folder path."
        if any(c in INVALID_CHARS for c in part):
            return None, f"Folder name contains invalid characters: {INVALID_CHARS}"
        if part.endswith((".", " ")):
            return None, "Folder name cannot end with a dot or a space."

    return text, None


def _slug(name: str) -> str:
    slug = re.sub(r'[<>:"/\\|?*\s]+', "_", name.strip()).strip("._").lower()
    return slug or "template"


def _safe_try_grab(win):
    try:
        win.wait_visibility()
        win.grab_set()
    except tk.TclError:
        pass


# ---------------------------------------------------------
# Dialog: add file to template
# ---------------------------------------------------------

def _open_file_dialog(parent, files_dir: Path, dirs: list, on_ok):
    dlg = tk.Toplevel(parent)
    dlg.title("Add template file")
    dlg.resizable(False, False)
    dlg.transient(parent)

    frame = ttk.Frame(dlg, padding=12)
    frame.pack(fill="both", expand=True)

    def available_files():
        if not files_dir.is_dir():
            return []
        return sorted(
            p.name for p in files_dir.iterdir()
            if p.is_file() and p.suffix.lower() != ".json"
        )

    # file
    ttk.Label(frame, text=f"File from {files_dir}:").grid(
        row=0, column=0, columnspan=2, sticky="w"
    )

    file_var = tk.StringVar()
    file_combo = ttk.Combobox(
        frame, textvariable=file_var, state="readonly",
        values=available_files(), width=40,
    )
    file_combo.grid(row=1, column=0, sticky="ew", pady=(4, 8))

    def browse():
        path = filedialog.askopenfilename(parent=dlg)
        if not path:
            return

        src = Path(path)
        dst = files_dir / src.name

        try:
            files_dir.mkdir(parents=True, exist_ok=True)

            same = dst.exists() and dst.resolve() == src.resolve()

            if dst.exists() and not same:
                if not messagebox.askyesno(
                    "Add file",
                    f"{src.name} already exists in templates.\nOverwrite?",
                    parent=dlg,
                ):
                    return

            if not same:
                shutil.copy2(src, dst)

        except OSError as error:
            messagebox.showerror("Add file", str(error), parent=dlg)
            return

        file_combo["values"] = available_files()
        file_var.set(src.name)

    ttk.Button(frame, text="Browse…", command=browse).grid(
        row=1, column=1, padx=(6, 0), pady=(4, 8)
    )

    # rename
    rename_var = tk.BooleanVar(value=False)
    name_var = tk.StringVar()

    name_entry = ttk.Entry(frame, textvariable=name_var, state="disabled")

    def toggle_rename():
        name_entry.config(state="normal" if rename_var.get() else "disabled")

    ttk.Checkbutton(
        frame, text="Rename file (extension is kept automatically)",
        variable=rename_var, command=toggle_rename,
    ).grid(row=2, column=0, columnspan=2, sticky="w")

    name_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 8))

    # targets
    ttk.Label(frame, text="Copy to (select one or more):").grid(
        row=4, column=0, sticky="w"
    )

    targets = tk.Listbox(
        frame, selectmode="multiple", height=6, exportselection=False
    )
    targets.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 8))

    for d in dirs:
        targets.insert("end", _dir_label(d))
    if dirs:
        targets.selection_set(0)

    def ok():
        template = file_var.get().strip()
        if not template:
            messagebox.showwarning("Add file", "Select a file.", parent=dlg)
            return

        is_rename = rename_var.get()
        new_name = name_var.get().strip()

        if is_rename:
            if not new_name or any(c in INVALID_CHARS + "/\\" for c in new_name):
                messagebox.showwarning("Add file", "Invalid new name.", parent=dlg)
                return
        else:
            new_name = ""

        chosen = [dirs[i] for i in targets.curselection()]
        if not chosen:
            messagebox.showwarning(
                "Add file", "Select at least one directory.", parent=dlg
            )
            return

        on_ok({
            "template": template,
            "is_rename": is_rename,
            "new_name": new_name,
            "dirs": chosen,
        })
        dlg.destroy()

    buttons = ttk.Frame(frame)
    buttons.grid(row=6, column=0, columnspan=2, sticky="e")
    ttk.Button(buttons, text="Add", command=ok).pack(side="left", padx=(0, 8))
    ttk.Button(buttons, text="Cancel", command=dlg.destroy).pack(side="left")

    dlg.bind("<Escape>", lambda e: dlg.destroy())
    _safe_try_grab(dlg)


# ---------------------------------------------------------
# Main editor (create / edit)
# ---------------------------------------------------------

def open_template_editor(root, configs_dir, files_dir, on_saved=None, existing=None):
    """
    configs_dir - куда сохраняется <name>.json (tool_kit/db/tasks_templates)
    files_dir   - откуда берутся файлы-заготовки (temp/templates)
    on_saved    - on_saved(template_name) после успешного сохранения
    existing    - {"file": "x.json", "data": {...}} -> режим редактирования,
                  None -> создание нового шаблона
    Возвращает окно (чтобы вызывающий мог сделать wait_window).
    """
    configs_dir = Path(configs_dir)
    files_dir = Path(files_dir)

    is_edit = existing is not None
    data0 = (existing or {}).get("data", {}) or {}

    # ---- начальное состояние ----
    dirs: list[str] = [str(d) for d in data0.get("dirs", [])] or [_dir_value("")]

    cfg0 = data0.get("copy_from_temp", {}) or {}
    copy_dirs: set[str] = {str(d) for d in cfg0.get("dirs", []) if str(d) in dirs}
    initial_is_copy = bool(cfg0.get("is_copy", False))

    files: list[dict] = []
    for f in data0.get("files", []):
        if isinstance(f, dict) and f.get("template"):
            files.append({
                "template": str(f["template"]),
                "is_rename": bool(f.get("is_rename", False)),
                "new_name": str(f.get("new_name", "") or ""),
                "dirs": [str(d) for d in f.get("dirs", [])],
            })

    # ---- window ----
    window = tk.Toplevel(root)
    window.title("Edit template" if is_edit else "New template")
    window.resizable(False, False)
    window.transient(root)

    frame = ttk.Frame(window, padding=15)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(0, weight=1)

    # ---- name ----
    ttk.Label(frame, text="Template name:").grid(row=0, column=0, sticky="w")
    name_var = tk.StringVar(value=str(data0.get("name", "")))
    name_entry = ttk.Entry(frame, textvariable=name_var, width=60)
    name_entry.grid(row=1, column=0, sticky="ew", pady=(4, 12))

    # ---- directories ----
    dirs_frame = ttk.LabelFrame(frame, text="Directories to create", padding=8)
    dirs_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
    dirs_frame.columnconfigure(0, weight=1)

    dirs_list = tk.Listbox(dirs_frame, height=5, exportselection=False)
    dirs_list.grid(row=0, column=0, columnspan=3, sticky="ew")

    sub_var = tk.StringVar()
    sub_entry = ttk.Entry(dirs_frame, textvariable=sub_var)
    sub_entry.grid(row=1, column=0, sticky="ew", pady=(6, 0))

    # ---- copy from temp ----
    copy_frame = ttk.LabelFrame(frame, text="Copy from temp", padding=8)
    copy_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
    copy_frame.columnconfigure(0, weight=1)

    copy_var = tk.BooleanVar(value=initial_is_copy)

    copy_list = tk.Listbox(
        copy_frame, selectmode="multiple", height=4, exportselection=False,
    )

    def toggle_copy():
        copy_list.config(state="normal" if copy_var.get() else "disabled")

    ttk.Checkbutton(
        copy_frame,
        text="Copy everything from temp/ (except temp/templates) to selected dirs, then clear temp/",
        variable=copy_var, command=toggle_copy,
    ).grid(row=0, column=0, sticky="w")

    copy_list.grid(row=1, column=0, sticky="ew", pady=(6, 0))

    def on_copy_select(event=None):
        copy_dirs.clear()
        copy_dirs.update(dirs[i] for i in copy_list.curselection())

    copy_list.bind("<<ListboxSelect>>", on_copy_select)

    # ---- files ----
    files_frame = ttk.LabelFrame(frame, text="Template files (copy-paste)", padding=8)
    files_frame.grid(row=4, column=0, sticky="ew", pady=(0, 10))
    files_frame.columnconfigure(0, weight=1)

    tree = ttk.Treeview(
        files_frame, columns=("file", "name", "dirs"),
        show="headings", height=5,
    )
    tree.heading("file", text="File")
    tree.heading("name", text="New name")
    tree.heading("dirs", text="Directories")
    tree.column("file", width=140)
    tree.column("name", width=120)
    tree.column("dirs", width=240)
    tree.grid(row=0, column=0, columnspan=3, sticky="ew")

    # ---- refresh helpers ----
    def refresh_dirs():
        # у disabled Listbox insert/delete не работают
        copy_list.config(state="normal")

        dirs_list.delete(0, "end")
        copy_list.delete(0, "end")

        for i, d in enumerate(dirs):
            dirs_list.insert("end", _dir_label(d))
            copy_list.insert("end", _dir_label(d))
            if d in copy_dirs:
                copy_list.selection_set(i)

        copy_list.config(state="normal" if copy_var.get() else "disabled")

    def refresh_files():
        tree.delete(*tree.get_children())
        for f in files:
            tree.insert("", "end", values=(
                f["template"],
                f["new_name"] if f["is_rename"] else "-",
                ", ".join(_dir_label(d) for d in f["dirs"]),
            ))

    # ---- dir actions ----
    def add_dir(event=None):
        sub, error = _clean_sub(sub_var.get())
        if error:
            messagebox.showwarning("Template", error, parent=window)
            return

        value = _dir_value(sub)
        if value in dirs:
            messagebox.showinfo(
                "Template", "This directory is already in the list.", parent=window
            )
            return

        dirs.append(value)
        sub_var.set("")
        refresh_dirs()

    def remove_dir():
        selection = dirs_list.curselection()
        if not selection:
            return

        value = dirs[selection[0]]
        dirs.remove(value)
        copy_dirs.discard(value)

        for f in files:
            if value in f["dirs"]:
                f["dirs"].remove(value)
        files[:] = [f for f in files if f["dirs"]]

        refresh_dirs()
        refresh_files()

    ttk.Button(dirs_frame, text="Add", command=add_dir).grid(
        row=1, column=1, padx=(6, 0), pady=(6, 0)
    )
    ttk.Button(dirs_frame, text="Remove", command=remove_dir).grid(
        row=1, column=2, padx=(6, 0), pady=(6, 0)
    )
    ttk.Label(
        dirs_frame, text="Subfolder, e.g. backup or src/utils (empty = project root)"
    ).grid(row=2, column=0, columnspan=3, sticky="w")

    sub_entry.bind("<Return>", add_dir)

    # ---- file actions ----
    def add_file():
        try:
            files_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            messagebox.showerror("Template", str(error), parent=window)
            return

        if not dirs:
            messagebox.showwarning(
                "Template", "Add at least one directory first.", parent=window
            )
            return

        def on_ok(entry):
            files.append(entry)
            refresh_files()

        _open_file_dialog(window, files_dir, dirs, on_ok)

    def remove_file():
        selection = tree.selection()
        if not selection:
            return
        files.pop(tree.index(selection[0]))
        refresh_files()

    ttk.Button(files_frame, text="Add file…", command=add_file).grid(
        row=1, column=1, padx=(0, 6), pady=(6, 0), sticky="e"
    )
    ttk.Button(files_frame, text="Remove", command=remove_file).grid(
        row=1, column=2, pady=(6, 0)
    )

    # ---- save ----
    def save():
        name = name_var.get().strip()

        if not name:
            messagebox.showwarning("Template", "Enter template name.", parent=window)
            name_entry.focus_set()
            return

        if not dirs:
            messagebox.showwarning(
                "Template", "Add at least one directory.", parent=window
            )
            return

        is_copy = copy_var.get()
        selected_copy = [d for d in dirs if d in copy_dirs] if is_copy else []

        if is_copy and not selected_copy:
            messagebox.showwarning(
                "Template",
                "Select at least one directory to copy temp files to.",
                parent=window,
            )
            return

        # сохраняем и неизвестные ключи, если они были в исходном json
        data = dict(data0)
        data.update({
            "name": name,
            "dirs": list(dirs),
            "copy_from_temp": {"is_copy": is_copy, "dirs": selected_copy},
            "files": files,
        })

        if is_edit:
            # редактирование: пишем в тот же файл
            path = configs_dir / existing["file"]
        else:
            path = configs_dir / f"{_slug(name)}.json"

            if path.exists() and not messagebox.askyesno(
                "Template",
                f"{path.name} already exists.\nOverwrite?",
                parent=window,
            ):
                return

        try:
            configs_dir.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
        except OSError as error:
            messagebox.showerror("Template", str(error), parent=window)
            return

        messagebox.showinfo("Template", f"Template saved:\n{path}", parent=window)

        window.destroy()

        if on_saved:
            on_saved(name)

    # ---- buttons ----
    buttons = ttk.Frame(frame)
    buttons.grid(row=5, column=0, sticky="e")

    ttk.Button(buttons, text="Save template", command=save).pack(
        side="left", padx=(0, 8)
    )
    ttk.Button(buttons, text="Cancel", command=window.destroy).pack(side="left")

    window.bind("<Escape>", lambda e: window.destroy())

    # ---- init ----
    refresh_dirs()
    refresh_files()

    window.update_idletasks()
    w, h = window.winfo_reqwidth(), window.winfo_reqheight()
    x = (window.winfo_screenwidth() - w) // 2
    y = (window.winfo_screenheight() - h) // 2
    window.geometry(f"+{x}+{y}")

    _safe_try_grab(window)
    name_entry.focus_set()

    return window