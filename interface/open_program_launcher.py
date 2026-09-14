import tkinter as tk

from scripts.program_launcher import get_programs
from scripts.settings_manager import write_settings


def open_program_launcher(root, BASE_DIR, BASE_SETTINGS):

    window = tk.Toplevel(root)
    window.title("Program launcher")

    programs = get_programs()

    variables = {}

    for name in programs:

        value = BASE_SETTINGS.get("PROGRAMS", {}).get(
            name,
            False
        )

        var = tk.BooleanVar(value=value)
        variables[name] = var

        tk.Checkbutton(
            window,
            text=name,
            variable=var,
            anchor="w"
        ).pack(
            fill="x",
            padx=10,
            pady=2
        )

    def save_settings():

        BASE_SETTINGS["PROGRAMS"] = {
            name: var.get()
            for name, var in variables.items()
        }

        write_settings(
            directory=BASE_DIR,
            settings=BASE_SETTINGS
        )

    def save_and_close():
        save_settings()
        window.destroy()

    buttons_frame = tk.Frame(window)
    buttons_frame.pack(
        fill="x",
        pady=10
    )

    tk.Button(
        buttons_frame,
        text="Save",
        command=save_and_close
    ).pack(
        side="left",
        expand=True,
        fill="x",
        padx=5
    )

    tk.Button(
        buttons_frame,
        text="Cancel",
        command=window.destroy
    ).pack(
        side="left",
        expand=True,
        fill="x",
        padx=5
    )

    window.update_idletasks()

    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()

    window.geometry(
        f"{width + 20}x{height + 20}"
    )