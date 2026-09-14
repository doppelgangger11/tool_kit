import argparse
from pathlib import Path

from scripts.init import initialize_project
from scripts.activation_new_task import activate_new_task
from scripts.settings_manager import read_settings, write_settings

from interface.open_settings_window import open_settings
from interface.open_activation_window import open_activation

from games.minesweeper.main import main as mineswipper_main
from games.tic_tac_toe.main import main as tic_tac_toe_main

import threading
import traceback
import tkinter as tk
# from scripts.main import main
from tkinter import messagebox


BASE_DIR = Path('./')

BASE_SETTINGS = read_settings(directory=BASE_DIR)

root = tk.Tk()
root.title("Toolkit")

label = tk.Label(root, text="Greetings!")
label.pack(pady=10)

warning_label = tk.Label(
    root, 
    text="⚠ WARNING: check working dir in `Settings`", 
    fg="red", font=("Arial", 8)
)
warning_label.pack(pady=(0, 5))

# Acrivate new task
activation_button = tk.Button(
    root,
    text='Activate new task',
    command=lambda: open_activation(
        root=root,
        WORKING_DIR=Path(BASE_SETTINGS["DIRS"]["working_dir"]),
        BASE_SETTINGS=BASE_SETTINGS
    )
)
activation_button.pack(pady=10)

mineswipper_button = tk.Button(
    root,
    text='mineswipper',
    command=mineswipper_main
)
mineswipper_button.pack(pady=10)

tic_tac_toe_main_button = tk.Button(
    root,
    text='tic-tac-toe',
    command=tic_tac_toe_main
)
tic_tac_toe_main_button.pack(pady=10)

# Settings
settings_button = tk.Button(
    root,
    text='Settings',
    command=lambda: open_settings(
        root=root,
        BASE_DIR=BASE_DIR,
        BASE_SETTINGS=BASE_SETTINGS
    )
)
settings_button.pack(pady=10)

tk.Button(root, text="Exit", command=root.destroy).pack()

root.update_idletasks()

width = root.winfo_reqwidth()
height = root.winfo_reqheight()

root.geometry(f"{width + 20}x{height + 20}")
root.mainloop()

