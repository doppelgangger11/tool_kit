import tkinter as tk
from pathlib import Path

from scripts.settings_manager import write_settings
from scripts.program_launcher import get_programs


def open_settings(root, BASE_DIR, BASE_SETTINGS):

    # =========================================================
    # Save settings
    # =========================================================

    def save_settings():

        # Save working directory
        new_dir = working_path_inp.get()

        if new_dir != '':
            BASE_SETTINGS["DIRS"]["working_dir"] = new_dir

        # Save logging setting
        BASE_SETTINGS["BASE"]["log"] = log_var.get()

        # Save selected programs
        BASE_SETTINGS["PROGRAMS"] = {
            name: var.get()
            for name, var in program_variables.items()
        }

        # Save architecture
        BASE_SETTINGS["ARCHITECTURE"] = architecture.copy()

        # Save architecture
        BASE_SETTINGS["ARCHITECTURE"] = architecture.copy()
    
        BASE_SETTINGS["ARCHITECTURE"]["activation_dir"] = (
            activation_dir_var.get()
        )

        # Write settings to settings.ini
        write_settings(
            directory=BASE_DIR,
            settings=BASE_SETTINGS
        )

        # Update current working directory label
        working_path_current.config(
            text=(
                "Current working dir: "
                f"{BASE_SETTINGS['DIRS']['working_dir']}"
            )
        )

    # =========================================================
    # Settings window
    # =========================================================

    window = tk.Toplevel(root)
    window.title("Settings")

    # =========================================================
    # Working directory
    # =========================================================

    working_path_label = tk.Label(
        window,
        text="Enter the base path"
    )
    working_path_label.pack(pady=10)

    working_path_inp = tk.Entry(
        window,
        width=30
    )
    working_path_inp.pack(pady=5)

    working_path_current = tk.Label(
        window,
        text=(
            "Current working dir: "
            f"{BASE_SETTINGS['DIRS']['working_dir']}"
        )
    )
    working_path_current.pack(pady=10)

    # =========================================================
    # Logging
    # =========================================================

    log_var = tk.BooleanVar(
        value=BASE_SETTINGS["BASE"]["log"]
    )

    log_checkbox = tk.Checkbutton(
        window,
        text="Turn on logging",
        variable=log_var,
        anchor="w"
    )
    log_checkbox.pack(
        fill="x",
        padx=5
    )

    # =========================================================
    # Architecture
    # =========================================================

    architecture_label = tk.Label(
        window,
        text="Architecture:"
    )
    architecture_label.pack(
        anchor="w",
        padx=10,
        pady=(15, 2)
    )

    # Copy architecture so changes are not written
    # to BASE_SETTINGS until Save is pressed.
    architecture = BASE_SETTINGS.get(
        "ARCHITECTURE",
        {}
    ).copy()
    
    activation_dir_var = tk.StringVar(
        value=architecture.get(
            "activation_dir",
            ""
        )
    )

    # ---------------------------------------------------------
    # Activation directory
    # ---------------------------------------------------------

    activation_dir_frame = tk.Frame(window)

    activation_dir_frame.pack(
        fill="x",
        padx=10,
        pady=5
    )

    activation_dir_label = tk.Label(
        activation_dir_frame,
        text=(
            "Activation directory: "
            f"{activation_dir_var.get()}"
        )
    )

    activation_dir_label.pack(
        side="left"
    )


    def select_activation_dir():

        dialog = tk.Toplevel(window)

        dialog.title("Select activation directory")
        dialog.geometry("300x250")
        dialog.resizable(False, False)

        dialog.transient(window)
        dialog.grab_set()

        tk.Label(
            dialog,
            text="Select directory:"
        ).pack(
            anchor="w",
            padx=10,
            pady=10
        )

        selected_var = tk.StringVar(
            value=activation_dir_var.get()
        )

        for name in architecture:

            if name == "activation_dir":
                continue

            tk.Radiobutton(
                dialog,
                text=name,
                variable=selected_var,
                value=name,
                anchor="w"
            ).pack(
                fill="x",
                padx=15,
                pady=2
            )

        def apply():

            selected = selected_var.get()

            if not selected:
                return

            activation_dir_var.set(selected)

            activation_dir_label.config(
                text=f"Activation directory: {selected}"
            )

            dialog.destroy()

        tk.Button(
            dialog,
            text="Apply",
            command=apply
        ).pack(
            fill="x",
            padx=10,
            pady=(15, 5)
        )

        tk.Button(
            dialog,
            text="Cancel",
            command=dialog.destroy
        ).pack(
            fill="x",
            padx=10
        )


    tk.Button(
        activation_dir_frame,
        text="Change...",
        command=select_activation_dir
    ).pack(
        side="right"
    )

    # ---------------------------------------------------------
    # Architecture list
    # ---------------------------------------------------------

    architecture_frame = tk.Frame(window)
    architecture_frame.pack(
        fill="x",
        padx=10,
        pady=5
    )

    architecture_list = tk.Listbox(
        architecture_frame,
        height=6
    )

    architecture_list.pack(
        side="left",
        fill="both",
        expand=True
    )

    architecture_scrollbar = tk.Scrollbar(
        architecture_frame,
        orient="vertical",
        command=architecture_list.yview
    )

    architecture_scrollbar.pack(
        side="right",
        fill="y"
    )

    architecture_list.config(
        yscrollcommand=architecture_scrollbar.set
    )

    # ---------------------------------------------------------
    # Refresh architecture list
    # ---------------------------------------------------------

    def update_architecture_list():

        architecture_list.delete(
            0,
            tk.END
        )

        for name, path in architecture.items():

            architecture_list.insert(
                tk.END,
                f"{name} = {path}"
            )

    update_architecture_list()

    # ---------------------------------------------------------
    # Folder dialog
    # ---------------------------------------------------------

    def open_folder_dialog(
        title,
        current_name="",
        current_path=""
    ):

        dialog = tk.Toplevel(window)
        dialog.title(title)
        dialog.geometry("400x180")
        dialog.resizable(False, False)

        dialog.transient(window)
        dialog.grab_set()

        # Name
        tk.Label(
            dialog,
            text="Name:"
        ).pack(
            anchor="w",
            padx=10,
            pady=(10, 2)
        )

        name_entry = tk.Entry(
            dialog,
            width=40
        )
        name_entry.pack(
            fill="x",
            padx=10
        )

        name_entry.insert(
            0,
            current_name
        )

        # Path
        tk.Label(
            dialog,
            text="Path:"
        ).pack(
            anchor="w",
            padx=10,
            pady=(10, 2)
        )

        path_entry = tk.Entry(
            dialog,
            width=40
        )
        path_entry.pack(
            fill="x",
            padx=10
        )

        path_entry.insert(
            0,
            current_path
        )

        result = {}

        def accept():

            name = name_entry.get().strip()
            path = path_entry.get().strip()

            if name == '' or path == '':
                return

            result["name"] = name
            result["path"] = path

            dialog.destroy()

        tk.Button(
            dialog,
            text="OK",
            command=accept
        ).pack(
            fill="x",
            padx=10,
            pady=10
        )

        window.wait_window(dialog)

        return result

    # ---------------------------------------------------------
    # Add folder
    # ---------------------------------------------------------

    def add_architecture_folder():

        result = open_folder_dialog(
            "Add architecture folder"
        )

        if not result:
            return

        name = result["name"]
        path = result["path"]

        if name in architecture:
            return

        architecture[name] = path

        update_architecture_list()

    # ---------------------------------------------------------
    # Edit folder
    # ---------------------------------------------------------

    def edit_architecture_folder():

        selection = architecture_list.curselection()

        if not selection:
            return

        index = selection[0]

        name = list(
            architecture.keys()
        )[index]

        path = architecture[name]

        result = open_folder_dialog(
            "Edit architecture folder",
            name,
            path
        )

        if not result:
            return

        new_name = result["name"]
        new_path = result["path"]

        if (
            new_name != name
            and new_name in architecture
        ):
            return

        del architecture[name]

        architecture[new_name] = new_path

        update_architecture_list()

    # ---------------------------------------------------------
    # Remove folder
    # ---------------------------------------------------------

    def remove_architecture_folder():

        selection = architecture_list.curselection()

        if not selection:
            return

        index = selection[0]

        name = list(
            architecture.keys()
        )[index]

        # Required by activation_new_task
        if name in (
            "active",
            "active_backup"
        ):
            return

        del architecture[name]

        update_architecture_list()

    # ---------------------------------------------------------
    # Create folders
    # ---------------------------------------------------------

    def create_architecture():

        working_dir = Path(
            BASE_SETTINGS["DIRS"]["working_dir"]
        )

        for path in architecture.values():

            directory = working_dir / path

            if working_dir / BASE_SETTINGS['ARCHITECTURE']['activation_dir'] != directory:
            
                directory.mkdir(
                    parents=True,
                    exist_ok=True
                )

    # ---------------------------------------------------------
    # Architecture buttons
    # ---------------------------------------------------------

    architecture_buttons = tk.Frame(window)
    architecture_buttons.pack(
        fill="x",
        padx=10,
        pady=(0, 5)
    )

    tk.Button(
        architecture_buttons,
        text="Add",
        command=add_architecture_folder
    ).pack(
        side="left",
        padx=2
    )

    tk.Button(
        architecture_buttons,
        text="Edit",
        command=edit_architecture_folder
    ).pack(
        side="left",
        padx=2
    )

    tk.Button(
        architecture_buttons,
        text="Remove",
        command=remove_architecture_folder
    ).pack(
        side="left",
        padx=2
    )

    tk.Button(
        architecture_buttons,
        text="Create folders",
        command=create_architecture
    ).pack(
        side="right",
        padx=2
    )

    # =========================================================
    # Programs
    # =========================================================

    programs_label = tk.Label(
        window,
        text="Startup programs:"
    )
    programs_label.pack(
        anchor="w",
        padx=10,
        pady=(15, 2)
    )

    # Search field
    search_var = tk.StringVar()

    search_entry = tk.Entry(
        window,
        textvariable=search_var
    )
    search_entry.pack(
        fill="x",
        padx=10,
        pady=(0, 5)
    )

    # =========================================================
    # Scrollable programs list
    # =========================================================

    programs_frame = tk.Frame(window)
    programs_frame.pack(
        fill="both",
        expand=True,
        padx=10,
        pady=5
    )

    canvas = tk.Canvas(
        programs_frame
    )

    scrollbar = tk.Scrollbar(
        programs_frame,
        orient="vertical",
        command=canvas.yview
    )

    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda event: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window(
        (0, 0),
        window=scrollable_frame,
        anchor="nw"
    )

    canvas.configure(
        yscrollcommand=scrollbar.set
    )

    canvas.pack(
        side="left",
        fill="both",
        expand=True
    )

    scrollbar.pack(
        side="right",
        fill="y"
    )

    # =========================================================
    # Get installed programs
    # =========================================================

    programs = get_programs()

    program_variables = {}

    for name in programs:

        current_value = BASE_SETTINGS.get(
            "PROGRAMS",
            {}
        ).get(
            name,
            False
        )

        program_variables[name] = tk.BooleanVar(
            value=current_value
        )

    # =========================================================
    # Update program list
    # =========================================================

    def update_program_list(*args):

        search = search_var.get().lower()

        for widget in scrollable_frame.winfo_children():
            widget.destroy()

        for name, variable in program_variables.items():

            if search not in name.lower():
                continue

            tk.Checkbutton(
                scrollable_frame,
                text=name,
                variable=variable,
                anchor="w"
            ).pack(
                fill="x",
                padx=5,
                pady=1
            )

        canvas.configure(
            scrollregion=canvas.bbox("all")
        )

    search_var.trace_add(
        "write",
        update_program_list
    )

    update_program_list()

    # =========================================================
    # Mouse wheel scrolling
    # =========================================================

    def on_mousewheel(event):

        canvas.yview_scroll(
            int(-1 * (event.delta / 120)),
            "units"
        )

    canvas.bind(
        "<Enter>",
        lambda event: canvas.bind_all(
            "<MouseWheel>",
            on_mousewheel
        )
    )

    canvas.bind(
        "<Leave>",
        lambda event: canvas.unbind_all(
            "<MouseWheel>"
        )
    )

    # =========================================================
    # Buttons
    # =========================================================

    buttons_frame = tk.Frame(window)
    buttons_frame.pack(
        fill="x",
        pady=10
    )

    buttons_frame.columnconfigure(
        0,
        weight=1
    )

    buttons_frame.columnconfigure(
        1,
        weight=1
    )

    def save_and_close():

        save_settings()
        window.destroy()

    tk.Button(
        buttons_frame,
        text="Save and back",
        command=save_and_close
    ).grid(
        row=0,
        column=0,
        sticky="nsew",
        padx=10,
        pady=10
    )

    tk.Button(
        buttons_frame,
        text="Cancel",
        command=window.destroy
    ).grid(
        row=0,
        column=1,
        sticky="nsew",
        padx=10,
        pady=10
    )

    # =========================================================
    # Automatically calculate window size
    # =========================================================

    window.update_idletasks()

    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()

    screen_height = window.winfo_screenheight()

    height = min(
        height + 20,
        screen_height - 100
    )

    window.geometry(
        f"{width + 20}x{height}")