import os
import tkinter as tk

from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from scripts.program_launcher import (
    CUSTOM_DIR,
    add_custom_program,
    get_programs,
    load_custom_programs,
    remove_custom_program,
)
from scripts.settings_manager import write_settings


def open_program_settings(root, BASE_DIR, BASE_SETTINGS):

    window = tk.Toplevel(root)
    window.title("Program settings")
    window.geometry("480x560")
    window.minsize(380, 360)

    if root.state() == "normal":
        window.transient(root)

    window.columnconfigure(0, weight=1)
    window.rowconfigure(1, weight=1)

    saved = BASE_SETTINGS.get("PROGRAMS", {})
    variables: dict[str, tk.BooleanVar] = {}
    checks: dict[str, ttk.Checkbutton] = {}

    # ---------------- search ----------------

    search_var = tk.StringVar()
    ttk.Entry(window, textvariable=search_var).grid(
        row=0, column=0, sticky="ew", padx=10, pady=(10, 6)
    )

    # ---------------- scrollable list ----------------

    area = ttk.Frame(window)
    area.grid(row=1, column=0, sticky="nsew", padx=10)
    area.rowconfigure(0, weight=1)
    area.columnconfigure(0, weight=1)

    canvas = tk.Canvas(area, highlightthickness=0)
    scrollbar = ttk.Scrollbar(area, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    inner = ttk.Frame(canvas)
    inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    inner.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.bind(
        "<Configure>",
        lambda e: canvas.itemconfigure(inner_id, width=e.width),
    )

    def on_wheel(event):
        canvas.yview_scroll(int(-event.delta / 120), "units")

    window.bind("<MouseWheel>", on_wheel)

    # ---------------- list logic ----------------

    def apply_filter(*_):
        needle = search_var.get().strip().lower()

        for check in checks.values():
            check.pack_forget()

        for name, check in checks.items():
            if not needle or needle in name.lower():
                check.pack(fill="x", anchor="w", pady=1)

        canvas.yview_moveto(0)

    def rebuild():
        state = {name: var.get() for name, var in variables.items()}

        for widget in inner.winfo_children():
            widget.destroy()

        variables.clear()
        checks.clear()

        for name, program in get_programs().items():
            value = state.get(name, bool(saved.get(name, False)))
            var = tk.BooleanVar(value=value)
            variables[name] = var

            text = name
            if program.source == "custom":
                text += "   [custom]"
            elif program.source == "folder":
                text += "   [folder]"

            checks[name] = ttk.Checkbutton(inner, text=text, variable=var)

        apply_filter()

    search_var.trace_add("write", apply_filter)

    # ---------------- custom programs dialog ----------------

    def open_custom_dialog():
        dlg = tk.Toplevel(window)
        dlg.title("Custom programs")
        dlg.transient(window)
        dlg.minsize(560, 430)

        frame = ttk.Frame(dlg, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(
            frame,
            text="Programs that are not in the Start Menu. "
                 "No administrator rights needed.",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

        listbox = tk.Listbox(frame, height=6, exportselection=False)
        listbox.grid(row=1, column=0, columnspan=3, sticky="ew")

        name_var = tk.StringVar()
        target_var = tk.StringVar()
        args_var = tk.StringVar()

        ttk.Label(frame, text="Name").grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        name_entry = ttk.Entry(frame, textvariable=name_var)
        name_entry.grid(
            row=2, column=1, columnspan=2, sticky="ew", pady=(10, 0)
        )

        ttk.Label(frame, text="Target").grid(
            row=3, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Entry(frame, textvariable=target_var).grid(
            row=3, column=1, sticky="ew", pady=(6, 0), padx=(0, 6)
        )

        ttk.Label(frame, text="Arguments").grid(
            row=4, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Entry(frame, textvariable=args_var).grid(
            row=4, column=1, columnspan=2, sticky="ew", pady=(6, 0)
        )

        ttk.Label(
            frame,
            wraplength=520,
            justify="left",
            text=(
                "Target: path to .exe / .lnk / .bat, or an address such as "
                "ms-teams:  Variables like %LOCALAPPDATA% work.\n\n"
                "New Teams:  target  ms-teams:\n"
                "Classic Teams:  target  %LOCALAPPDATA%\\Microsoft\\Teams\\"
                "Update.exe   arguments  --processStart \"Teams.exe\"\n\n"
                "You can also drop any shortcut into the Toolkit folder "
                "(button below) and it will appear in the list."
            ),
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(10, 0))

        names: list[str] = []

        def reload_list():
            names[:] = sorted(load_custom_programs(), key=str.lower)
            listbox.delete(0, "end")
            for name in names:
                listbox.insert("end", name)

        def clear_form():
            listbox.selection_clear(0, "end")
            name_var.set("")
            target_var.set("")
            args_var.set("")
            name_entry.config(state="normal")

        def on_select(event=None):
            selection = listbox.curselection()
            if not selection:
                return

            name = names[selection[0]]
            item = load_custom_programs().get(name, {})

            name_entry.config(state="normal")
            name_var.set(name)
            target_var.set(item.get("target", ""))
            args_var.set(item.get("args", ""))
            name_entry.config(state="disabled")

        def browse():
            path = filedialog.askopenfilename(
                parent=dlg,
                title="Select program",
                filetypes=[
                    ("Programs and shortcuts", "*.exe *.lnk *.bat *.cmd *.url"),
                    ("All files", "*.*"),
                ],
            )
            if not path:
                return

            target_var.set(str(Path(path)))
            if not name_var.get().strip():
                name_var.set(Path(path).stem)

        def save():
            name = name_var.get().strip()

            try:
                add_custom_program(name, target_var.get(), args_var.get())
            except ValueError as error:
                messagebox.showwarning(
                    "Custom programs", str(error), parent=dlg
                )
                return
            except OSError as error:
                messagebox.showerror(
                    "Custom programs", str(error), parent=dlg
                )
                return

            reload_list()
            rebuild()

            if name in variables:
                variables[name].set(True)

            if name in names:
                index = names.index(name)
                listbox.selection_clear(0, "end")
                listbox.selection_set(index)
                on_select()

        def remove():
            selection = listbox.curselection()
            if not selection:
                return

            name = names[selection[0]]

            if not messagebox.askyesno(
                "Custom programs",
                f"Remove '{name}' from Toolkit?\n\n"
                "The program itself will not be touched.",
                parent=dlg,
            ):
                return

            try:
                remove_custom_program(name)
            except OSError as error:
                messagebox.showerror(
                    "Custom programs", str(error), parent=dlg
                )
                return

            reload_list()
            clear_form()
            rebuild()

        def open_folder():
            try:
                CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
                os.startfile(CUSTOM_DIR)
            except (OSError, AttributeError) as error:
                messagebox.showerror(
                    "Custom programs", str(error), parent=dlg
                )

        ttk.Button(frame, text="Browse…", command=browse).grid(
            row=3, column=2, pady=(6, 0)
        )

        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(14, 0))

        ttk.Button(buttons, text="New", command=clear_form).pack(side="left")
        ttk.Button(buttons, text="Save", command=save).pack(
            side="left", padx=6
        )
        ttk.Button(buttons, text="Remove", command=remove).pack(side="left")
        ttk.Button(buttons, text="Open Toolkit folder", command=open_folder).pack(
            side="left", padx=(16, 0)
        )
        ttk.Button(buttons, text="Close", command=dlg.destroy).pack(
            side="right"
        )

        listbox.bind("<<ListboxSelect>>", on_select)
        dlg.bind("<Escape>", lambda e: dlg.destroy())

        reload_list()

        try:
            dlg.wait_visibility()
            dlg.grab_set()
        except tk.TclError:
            pass

    # ---------------- save / buttons ----------------

    def save_settings():
        BASE_SETTINGS["PROGRAMS"] = {
            name: var.get()
            for name, var in variables.items()
        }

        try:
            write_settings(directory=BASE_DIR, settings=BASE_SETTINGS)
        except OSError as error:
            messagebox.showerror(
                "Program settings", str(error), parent=window
            )
            return

        window.destroy()

    bottom = ttk.Frame(window)
    bottom.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

    ttk.Button(
        bottom, text="Custom programs…", command=open_custom_dialog
    ).pack(side="left")

    ttk.Button(bottom, text="Save", command=save_settings).pack(side="right")
    ttk.Button(bottom, text="Cancel", command=window.destroy).pack(
        side="right", padx=(0, 6)
    )

    rebuild()