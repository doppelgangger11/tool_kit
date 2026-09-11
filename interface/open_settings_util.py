import tkinter as tk
from scripts.settings_manager import read_settings, write_settings


def open_settings(root, BASE_DIR, BASE_SETTINGS):
    def save_settings():
        BASE_SETTINGS["DIRS"]["working_dir"] = working_path_inp.get()

        write_settings(
            directory=BASE_DIR,
            settings=BASE_SETTINGS
        )

        working_path_current.config(
            text=f"Current working dir: {BASE_SETTINGS['DIRS']['working_dir']}"
        )
    
    window = tk.Toplevel(root)
    window.title("Settings")
    
    working_path_lable = tk.Label(window, text="Enter the base path")
    working_path_lable.pack(pady=10)

    working_path_inp = tk.Entry(window, width=30)
    working_path_inp.pack(pady=5)
    
    working_path_current = tk.Label(
        window, 
        text=f'Current working dir: {BASE_SETTINGS["DIRS"]["working_dir"]}'
    )
    working_path_current.pack(pady=10)

    tk.Button(
        window,
        text="Save",
        command=save_settings
    ).pack(pady=5)
    
    tk.Button(
        window, 
        text="Back", 
        command=window.destroy
    ).pack()
    
if __name__ == '__main__':
    BASE_DIR = ""
    BASE_SETTINGS = dict()

    root = tk.Tk()