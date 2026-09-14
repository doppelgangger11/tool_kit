import tkinter as tk
from scripts.settings_manager import read_settings, write_settings


def open_settings(root, BASE_DIR, BASE_SETTINGS):
    def save_settings():
        new_dir = working_path_inp.get()
        if new_dir != '':
            BASE_SETTINGS["DIRS"]["working_dir"] = new_dir

        new_log = var.get()
        if new_log != BASE_SETTINGS["BASE"]["log"]:
            BASE_SETTINGS["BASE"]["log"] = new_log
            
        write_settings(
            directory=BASE_DIR,
            settings=BASE_SETTINGS
        )

        working_path_current.config(
            text=f"Current working dir: {BASE_SETTINGS['DIRS']['working_dir']}"
        )
    
    
    # Changing working path
    window = tk.Toplevel(root)
    window.title("Settings")
    # window.rowconfigure(0, weight=1)     # Строка 0 будет растягиваться
    # window.columnconfigure(0, weight=1)  # Столбец 0 для первой кнопки
    # window.columnconfigure(1, weight=1)  # Столбец 1 для второй кнопки
    
    working_path_lable = tk.Label(window, text="Enter the base path")
    working_path_lable.pack(pady=10)

    working_path_inp = tk.Entry(window, width=30)
    working_path_inp.pack(pady=5)
    
    working_path_current = tk.Label(
        window, 
        text=f'Current working dir: {BASE_SETTINGS["DIRS"]["working_dir"]}'
    )
    working_path_current.pack(pady=10)
    
    # Changing logs
    var = tk.BooleanVar(value=BASE_SETTINGS['BASE']['log'])  # включено по умолчанию
    cb = tk.Checkbutton(window, text='Turn on logging', variable=var, anchor="w")
    cb.pack(fill="x", padx=5)

    
    buttons_frame = tk.Frame(window)
    buttons_frame.pack(fill="x", pady=10)

    buttons_frame.columnconfigure(0, weight=1)
    buttons_frame.columnconfigure(1, weight=1)
    
    tk.Button(
        buttons_frame, 
        text="Save and back", 
        command=lambda: (
            save_settings(),
            window.destroy()
        )
    ).grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    tk.Button(
        buttons_frame, 
        text="Cancle", 
        command=window.destroy
    ).grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    
    window.update_idletasks()

    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()

    window.geometry(f"{width + 20}x{height + 20}")