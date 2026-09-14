import tkinter as tk

from scripts.program_launcher import get_programs
from scripts.settings_manager import write_settings


def open_program_settings(root, BASE_DIR, BASE_SETTINGS):

    window = tk.Toplevel(root)
    window.title("Program settings")

    programs = get_programs()
    variables = {}

    for name in programs:

        current_value = BASE_SETTINGS.get(
            "PROGRAMS",
            {}
        ).get(name, False)

        var = tk.BooleanVar(value=current_value)
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

        window.destroy()

    tk.Button(
        window,
        text="Save",
        command=save_settings
    ).pack(
        fill="x",
        padx=10,
        pady=10
    )

    window.update_idletasks()

    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()

    window.geometry(
        f"{width + 20}x{height + 20}"
    )