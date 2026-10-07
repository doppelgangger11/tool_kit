import sys
import tkinter as tk

from pathlib import Path

from scripts.daemon import Dispatcher, SingleInstance
from scripts.note_manager import NotesManager
from scripts.program_launcher import launch_selected_programs
from scripts.settings_manager import read_settings, ensure_structure

from interface.tray import Tray
from interface.quick_notes_window import open_notes
from interface.open_settings_window import open_settings
from interface.open_activation_window import open_activation
from interface.quick_commands_window import open_quick_commands

from games.minesweeper.main import main as mineswipper_main
from games.tic_tac_toe.main import main as tic_tac_toe_main
from games.chess.chess_interface import main as chess


BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------
# Один демон на компьютер
# ---------------------------------------------------------

instance = SingleInstance()

if not instance.acquire():
    print("[Toolkit] Already running - asked the running copy to show its window.")
    sys.exit(0)

# ---------------------------------------------------------
# Settings
# ---------------------------------------------------------

BASE_SETTINGS = read_settings(directory=BASE_DIR)
problems = ensure_structure(BASE_DIR, BASE_SETTINGS)

START_HIDDEN = (
    "--background" in sys.argv
    or bool(BASE_SETTINGS.get("BASE", {}).get("start_hidden", False))
)

# ---------------------------------------------------------
# Window
# ---------------------------------------------------------

root = tk.Tk()
root.title("Toolkit")

dispatcher = Dispatcher(root)

notes_manager = NotesManager(path=BASE_DIR / "db" / "notes.json")
notes_manager.read_notes()

BUTTONS = [
    ("launcher", "Launch work setup", launch_selected_programs, (BASE_SETTINGS,)),
    ("activation", "Activate new task", open_activation, (root, BASE_DIR, BASE_SETTINGS)),
    ("notes", "Quick Notes", open_notes, (root, notes_manager)),
    ("quick_commands", "Quick Commands", open_quick_commands, (root, BASE_DIR, BASE_SETTINGS)),
    ("chess", "Chess", chess, ()),
    ("mineswipper", "Mineswipper", mineswipper_main, ()),
    ("tic_tac_toe", "Tic-Tak-Toe", tic_tac_toe_main, ()),
    ("settings", "Settings", open_settings, (root, BASE_DIR, BASE_SETTINGS,)),
    ("exit", "Exit", root.destroy, ()),
]

# что показывать в меню трея (по ключам из BUTTONS)
TRAY_KEYS = ("launcher", "activation", "notes", "quick_commands")

tray_actions = [
    (text, lambda command=command, args=args: command(*args))
    for key, text, command, args in BUTTONS
    if key in TRAY_KEYS
]

tray = Tray(root, dispatcher, actions=tray_actions)

label = tk.Label(root, text="Greetings!")
label.pack(pady=10)

if problems:
    tk.Label(
        root,
        text="⚠ " + "\n".join(problems),
        fg="red", font=("Arial", 8), justify="left",
    ).pack(pady=(0, 5))

for icon_name, text, command, args in BUTTONS:

    tk.Button(
        root,
        text=text,
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

# ---------------------------------------------------------
# Daemon
# ---------------------------------------------------------

if START_HIDDEN:
    root.withdraw()

dispatcher.install_signal_handlers(tray.exit_app)     # Ctrl+C в терминале
instance.serve(lambda: dispatcher.call(tray.show_window))
tray.start()

print("[Toolkit] Running. Control it from the tray icon, Ctrl+C here to exit.")

try:
    root.mainloop()
finally:
    tray.stop()
    instance.close()
