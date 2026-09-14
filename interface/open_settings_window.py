import tkinter as tk

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

    # Canvas allows the program list to be scrolled
    canvas = tk.Canvas(
        programs_frame
    )

    # Vertical scrollbar
    scrollbar = tk.Scrollbar(
        programs_frame,
        orient="vertical",
        command=canvas.yview
    )

    # Frame inside the Canvas.
    # Checkbuttons will be placed here.
    scrollable_frame = tk.Frame(canvas)

    # Update scrollable area when the content changes
    scrollable_frame.bind(
        "<Configure>",
        lambda event: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    # Put scrollable_frame inside the Canvas
    canvas.create_window(
        (0, 0),
        window=scrollable_frame,
        anchor="nw"
    )

    # Connect scrollbar to Canvas
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

    # Store BooleanVars separately from Checkbuttons.
    #
    # This allows us to destroy and recreate Checkbuttons
    # during searching without losing their selected state.
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

        # Get current search text
        search = search_var.get().lower()

        # Remove currently displayed Checkbuttons
        for widget in scrollable_frame.winfo_children():
            widget.destroy()

        # Create Checkbuttons only for matching programs
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

        # Update Canvas scroll region
        canvas.configure(
            scrollregion=canvas.bbox("all")
        )

    # Update list whenever search text changes
    search_var.trace_add(
        "write",
        update_program_list
    )

    # Draw initial program list
    update_program_list()

    # =========================================================
    # Mouse wheel scrolling
    # =========================================================

    def on_mousewheel(event):

        canvas.yview_scroll(
            int(-1 * (event.delta / 120)),
            "units"
        )

    # Enable mouse wheel only when cursor is over the list
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

    # Save settings and close the window
    def save_and_close():

        save_settings()
        window.destroy()

    # Save button
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

    # Cancel button
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

    # Do not allow the window to become taller than the screen
    screen_height = window.winfo_screenheight()

    height = min(
        height + 20,
        screen_height - 100
    )

    window.geometry(
        f"{width + 20}x{height}"
    )