import tkinter as tk

from tkinter import ttk, messagebox

from interface.ui_utils import attach, bring_to_front
from scripts.hotkeys import parse_hotkey
from scripts.settings_manager import write_settings


GREEN, RED, GRAY = "#16803c", "#c53030", "#777777"

_instance = None


def open_hotkeys(root, base_dir, settings, service):
    """
    service - HotkeyService (он знает действия и умеет перерегистрировать клавиши)
    """
    global _instance

    if _instance is not None:
        try:
            if _instance.winfo_exists():
                bring_to_front(_instance)
                return _instance
        except tk.TclError:
            pass

    window = tk.Toplevel(root)
    _instance = window
    window.title("Global hotkeys")
    window.resizable(False, False)
    attach(window, root)

    frame = ttk.Frame(window, padding=14)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(1, weight=1)

    ttk.Label(
        frame, text="GLOBAL HOTKEYS", font=("Arial", 13, "bold")
    ).grid(row=0, column=0, columnspan=3, sticky="w")

    ttk.Label(
        frame,
        wraplength=520,
        justify="left",
        foreground="#555555",
        text="Format: Ctrl+Alt+N, Ctrl+Shift+F5, Win+Space. At least one "
             "modifier is required. Leave empty to turn an action off.\n"
             "A global hotkey takes the combination away from other programs "
             "(for example Ctrl+Alt+S in PyCharm), so pick something unusual.",
    ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 10))

    variables: dict[str, tk.StringVar] = {}
    labels: dict[str, ttk.Label] = {}

    for row, (key, (title, _func)) in enumerate(service.actions.items(), start=2):
        ttk.Label(frame, text=title).grid(row=row, column=0, sticky="w", pady=3)

        var = tk.StringVar(value=service.combo_for(key))
        variables[key] = var
        ttk.Entry(frame, textvariable=var, width=24).grid(
            row=row, column=1, sticky="w", padx=10
        )

        label = ttk.Label(frame, text="", width=34)
        label.grid(row=row, column=2, sticky="w")
        labels[key] = label

    def show_status():
        for key, label in labels.items():
            state, message = service.status.get(key, ("disabled", ""))

            if state == "ok":
                label.config(text=f"✓ active: {message}", foreground=GREEN)
            elif state == "error":
                label.config(text=f"✗ {message}", foreground=RED)
            else:
                label.config(text="off", foreground=GRAY)

    def save():
        values = {}
        failed = False

        for key, var in variables.items():
            text = var.get().strip()

            if not text:
                values[key] = ""
                continue

            try:
                _, _, canonical = parse_hotkey(text)
            except ValueError as error:
                labels[key].config(text=f"✗ {error}", foreground=RED)
                failed = True
                continue

            values[key] = canonical

        if failed:
            return

        service.settings.setdefault("HOTKEYS", {}).update(values)

        try:
            write_settings(directory=base_dir, settings=service.settings)
        except OSError as error:
            messagebox.showerror("Hotkeys", str(error), parent=window)
            return

        service.apply()

        for key, var in variables.items():
            var.set(values[key])

        show_status()

    buttons = ttk.Frame(frame)
    buttons.grid(row=len(service.actions) + 2, column=0, columnspan=3,
                 sticky="e", pady=(12, 0))

    ttk.Button(buttons, text="Save and apply", command=save).pack(
        side="left", padx=(0, 8)
    )
    ttk.Button(buttons, text="Close", command=window.destroy).pack(side="left")

    window.bind("<Escape>", lambda e: window.destroy())

    show_status()
    bring_to_front(window)

    return window