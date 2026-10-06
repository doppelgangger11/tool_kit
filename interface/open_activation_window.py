import json
import tkinter as tk

from pathlib import Path
from tkinter import ttk, messagebox

from scripts.activation_new_task import (
    TEMPLATES_DIR_NAME,
    TempCleanupError,
    activate_new_task,
    list_temp_items,
    validate_project_name,
)
from interface.open_template_editor import open_template_editor


def _resolve_path(working_dir: Path, path_value) -> Path:
    """
    "temp" и "/temp" -> <working_dir>/temp
    "C:/something"   -> как есть (абсолютный путь Windows)
    """
    path_value = str(path_value).strip()

    if not path_value:
        return working_dir

    path = Path(path_value)

    if path.drive:
        return path

    return working_dir / path_value.lstrip("/\\")


def _load_templates(configs_dir: Path):
    """
    Возвращает ({отображаемое имя: {"file": имя файла, "data": dict}}, [ошибки]).
    """
    templates = {}
    errors = []

    if not configs_dir.is_dir():
        return templates, errors

    for template_file in sorted(configs_dir.glob("*.json")):
        try:
            with template_file.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if not isinstance(data, dict):
                raise ValueError("root must be an object")

            name = str(data.get("name", "")).strip() or template_file.stem

            # одинаковые name у разных файлов не должны затирать друг друга
            if name in templates:
                name = f"{name} ({template_file.name})"

            templates[name] = {"file": template_file.name, "data": data}

        except (json.JSONDecodeError, OSError, ValueError) as error:
            errors.append(f"{template_file.name}: {error}")
            print(f"[Activation] Bad template {template_file.name}: {error}")

    return templates, errors


def _pretty(path_value) -> str:
    return (
        str(path_value)
        .replace("$active_folder$/", "")
        .replace("$active_folder$", "")
        .replace("$name_of_project$", "<project>")
    )


def open_activation(root, base_dir, settings):
    """
    root      - главное окно tk
    base_dir  - папка tool_kit (BASE_DIR), там лежит settings.ini и db/
    settings  - словарь из read_settings()
    """

    # ---------------- paths ----------------

    base_dir = Path(base_dir).resolve()

    dirs_cfg = settings.get("DIRS", {})
    arch_cfg = settings.get("ARCHITECTURE", {})

    working_dir = Path(str(dirs_cfg.get("working_dir", "") or ""))
    if not working_dir.is_absolute():
        working_dir = (base_dir / working_dir).resolve()

    temp_dir = _resolve_path(working_dir, dirs_cfg.get("temp_dir", "/temp"))
    active_dir = _resolve_path(working_dir, arch_cfg.get("active", "./active"))

    # .json описания шаблонов
    configs_dir = base_dir / "db" / "tasks_templates"
    # файлы-заготовки (dag.py, sql.sql, ...) - только читаем, не трогаем
    files_dir = temp_dir / TEMPLATES_DIR_NAME

    print(
        "[Activation] paths:\n"
        f"  base_dir    = {base_dir}\n"
        f"  working_dir = {working_dir}\n"
        f"  temp_dir    = {temp_dir}\n"
        f"  active_dir  = {active_dir}\n"
        f"  configs_dir = {configs_dir}\n"
        f"  files_dir   = {files_dir}"
    )

    templates = {}

    # ---------------- window ----------------

    window = tk.Toplevel(root)
    window.title("Activate Project")
    window.resizable(False, False)
    window.transient(root)

    frame = ttk.Frame(window, padding=15)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(0, weight=1)

    # project name
    ttk.Label(frame, text="Project name:").grid(row=0, column=0, sticky="w")

    name_var = tk.StringVar()
    name_entry = ttk.Entry(frame, textvariable=name_var, width=50)
    name_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 12))

    # template
    ttk.Label(frame, text="Template:").grid(row=2, column=0, sticky="w")

    template_var = tk.StringVar()
    combo = ttk.Combobox(frame, textvariable=template_var, state="readonly")
    combo.grid(row=3, column=0, sticky="ew", pady=(4, 12))

    refresh_btn = ttk.Button(frame, text="⟳", width=3)
    refresh_btn.grid(row=3, column=1, padx=(6, 0), pady=(4, 12))

    # template info
    info_frame = ttk.LabelFrame(frame, text="Template info", padding=8)
    info_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 12))
    info_frame.columnconfigure(0, weight=1)

    info_text = tk.Text(
        info_frame, width=60, height=10, wrap="none",
        relief="flat", state="disabled",
        background=window.cget("background"),
    )
    info_text.grid(row=0, column=0, sticky="ew")

    # temp info
    temp_frame = ttk.LabelFrame(frame, text="Temporary files", padding=8)
    temp_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 12))

    temp_label = ttk.Label(temp_frame, text="")
    temp_label.pack(anchor="w")

    temp_warn = tk.Label(temp_frame, text="", fg="red", justify="left", anchor="w")
    temp_warn.pack(anchor="w", fill="x")

    status_label = tk.Label(frame, text="", fg="red", justify="left", anchor="w")
    status_label.grid(row=6, column=0, columnspan=2, sticky="ew")

    # ---------------- logic ----------------

    def current_template():
        return templates.get(template_var.get())

    def set_info(text: str):
        info_text.config(state="normal")
        info_text.delete("1.0", "end")
        info_text.insert("1.0", text)
        info_text.config(state="disabled")

    def update_temp_info(event=None):
        if not temp_dir.is_dir():
            temp_label.config(text=f"Temp directory not found:\n{temp_dir}")
            temp_warn.config(text="")
            return

        items = list_temp_items(temp_dir)
        temp_label.config(text=f"Files in temp: {len(items)}  (templates/ is ignored)")

        warn = ""
        tpl = current_template()

        if items and tpl:
            cfg = tpl["data"].get("copy_from_temp", {}) or {}
            if not (cfg.get("is_copy", False) and cfg.get("dirs")):
                warn = (
                    "⚠ This template does not copy from temp,\n"
                    "files in temp will stay where they are."
                )

        temp_warn.config(text=warn)

    def update_template_info(event=None):
        tpl = current_template()

        if tpl is None:
            set_info("")
            update_temp_info()
            return

        data = tpl["data"]
        lines = [f"File: {tpl['file']}", ""]

        lines.append("Directories:")
        for d in data.get("dirs", []):
            lines.append(f"  {_pretty(d)}")

        cfg = data.get("copy_from_temp", {}) or {}
        lines.append("")
        if cfg.get("is_copy", False):
            lines.append("Copy from temp to:")
            for d in cfg.get("dirs", []):
                lines.append(f"  {_pretty(d)}")
        else:
            lines.append("Copy from temp: no")

        files = data.get("files", [])
        lines.append("")
        lines.append(f"Template files: {len(files)}")
        for f in files:
            target = (
                f.get("new_name")
                if f.get("is_rename") and f.get("new_name")
                else f.get("template", "")
            )
            lines.append(f"  {f.get('template', '')}  ->  {target}")

        set_info("\n".join(lines))
        update_temp_info()

    def reload_templates():
        nonlocal templates

        templates, errors = _load_templates(configs_dir)
        names = list(templates.keys())
        combo["values"] = names

        previous = template_var.get()

        if names:
            combo.current(names.index(previous) if previous in names else 0)
            activate_btn.state(["!disabled"])
        else:
            template_var.set("")
            activate_btn.state(["disabled"])

        status = []
        if not configs_dir.is_dir():
            status.append(f"Templates folder not found:\n{configs_dir}")
        elif not names:
            status.append(f"No templates found in:\n{configs_dir}")
        if errors:
            status.append("Invalid templates skipped:\n" + "\n".join(errors))

        status_label.config(text="\n".join(status))

        update_template_info()

    def on_template_saved(name):
        reload_templates()
        if name in templates:
            template_var.set(name)
            update_template_info()
            
    def edit_template():
        tpl = current_template()
        if tpl is None:
            return

        editor = open_template_editor(
            window, configs_dir, files_dir,
            on_saved=on_template_saved,
            existing=tpl,
        )
        window.wait_window(editor)
        if window.winfo_exists():
            window.grab_set()

    def delete_template():
        tpl = current_template()
        if tpl is None:
            return

        path = configs_dir / tpl["file"]

        if not messagebox.askyesno(
            "Delete template",
            f"Delete template '{template_var.get()}'?\n\n{path}\n\n"
            "Files in temp/templates will NOT be deleted.",
            icon="warning",
            parent=window,
        ):
            return

        try:
            path.unlink()
        except OSError as error:
            messagebox.showerror("Delete template", str(error), parent=window)
            return

        reload_templates()

    def open_editor():
        editor = open_template_editor(
            window, configs_dir, files_dir, on_saved=on_template_saved
        )
        window.wait_window(editor)
        if window.winfo_exists():
            window.grab_set()

    def on_activate(event=None):
        project_name = name_var.get().strip()

        error = validate_project_name(project_name)
        if error:
            messagebox.showwarning("Activation", error, parent=window)
            name_entry.focus_set()
            return

        tpl = current_template()
        if tpl is None:
            messagebox.showwarning("Activation", "Select a template.", parent=window)
            return

        try:
            active_dir.mkdir(parents=True, exist_ok=True)

            result = activate_new_task(
                base_dir=active_dir,
                name_of_task=project_name,
                tmp_dir=temp_dir,
                template_name=tpl["file"],
                configs_dir=configs_dir,
            )

        except TempCleanupError as error:
            messagebox.showwarning("Activation", str(error), parent=window)
            window.destroy()
            return

        except Exception as error:
            messagebox.showerror(
                "Activation error",
                f"{type(error).__name__}: {error}",
                parent=window,
            )
            update_temp_info()
            return

        text = f"Project created:\n{result.project_dir}"
        if result.temp_copied:
            text += "\n\nFiles from temp were copied and temp was cleaned."

        messagebox.showinfo("Activation", text, parent=window)
        window.destroy()

    # ---------------- buttons ----------------

    buttons = ttk.Frame(frame)
    buttons.grid(row=7, column=0, columnspan=2, sticky="e", pady=(12, 0))

    ttk.Button(buttons, text="New template…", command=open_editor).pack(
        side="left", padx=(0, 8)
    )

    edit_btn = ttk.Button(buttons, text="Edit…", command=edit_template)
    edit_btn.pack(side="left", padx=(0, 8))

    delete_btn = ttk.Button(buttons, text="Delete", command=delete_template)
    delete_btn.pack(side="left", padx=(0, 24))

    activate_btn = ttk.Button(buttons, text="Activate", command=on_activate)
    activate_btn.pack(side="left", padx=(0, 8))

    ttk.Button(buttons, text="Cancel", command=window.destroy).pack(side="left")

    refresh_btn.config(command=reload_templates)
    combo.bind("<<ComboboxSelected>>", update_template_info)
    window.bind("<Return>", on_activate)
    window.bind("<Escape>", lambda event: window.destroy())

    # ---------------- init ----------------

    reload_templates()

    window.update_idletasks()
    w, h = window.winfo_reqwidth(), window.winfo_reqheight()
    x = (window.winfo_screenwidth() - w) // 2
    y = (window.winfo_screenheight() - h) // 2
    window.geometry(f"+{x}+{y}")

    try:
        window.wait_visibility()
        window.grab_set()
    except tk.TclError:
        pass

    name_entry.focus_set()