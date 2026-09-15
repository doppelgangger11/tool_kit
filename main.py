import argparse
from pathlib import Path

from scripts.init import initialize_project
from scripts.activation_new_task import activate_new_task
from scripts.program_launcher import launch_selected_programs
from scripts.settings_manager import read_settings, write_settings
from scripts.note_manager import NotesManager

from interface.tray import setup_tray
from interface.open_settings_window import open_settings
from interface.open_activation_window import open_activation
from interface.open_program_launcher import open_program_launcher
from interface.open_program_settings import open_program_settings
from interface.quick_notes_window import open_notes

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

notes_manager = NotesManager(path=BASE_DIR / "db" / "notes.json")
notes_manager.read_notes()

BUTTONS = [
    ("launcher", "Launch work setup", launch_selected_programs, (BASE_SETTINGS,)),
    ("activation", "Activate new task", open_activation, (root, Path(BASE_SETTINGS["DIRS"]["working_dir"]), BASE_SETTINGS)),
    ("notes", "Quick Notes", open_notes, (root, notes_manager)),
    ("mineswipper", "Mineswipper", mineswipper_main, ()),
    ("tic_tac_toe", "Tic-Tak-Toe", tic_tac_toe_main, ()),
    ("settings", "Settings", open_settings, (root, BASE_DIR, BASE_SETTINGS,)),
    ("exit", "Exit", root.destroy, ()),
]

setup_tray(root)

label = tk.Label(root, text="Greetings!")
label.pack(pady=10)

warning_label = tk.Label(
    root, 
    text="⚠ WARNING: check working dir in `Settings`", 
    fg="red", font=("Arial", 8)
)
warning_label.pack(pady=(0, 5))

# Adding buttons
for icon_name, text, command, args in BUTTONS:

    tk.Button(
        root,
        text=text,
        # image=icons[icon_name],
        compound="left",
        command=lambda command=command, args=args: command(*args)
    ).pack(
        fill="x",
        padx=10,
        pady=5
    )

root.update_idletasks()

width = root.winfo_reqwidth()
height = root.winfo_reqheight()

root.geometry(f"{width + 20}x{height + 20}")
root.mainloop()

