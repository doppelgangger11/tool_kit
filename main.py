import sys
import tkinter as tk

from pathlib import Path

from scripts.daemon import Dispatcher, SingleInstance
from scripts.hotkey import GlobalHotkey
from scripts.note_manager import NotesManager
from scripts.registry import AppContext
from scripts.settings_manager import read_settings, ensure_structure

from interface.tray import Tray
from interface.launcher_window import Launcher
from modules import build_modules


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

ctx = AppContext(
    root=root,
    base_dir=BASE_DIR,
    settings=BASE_SETTINGS,
    notes_manager=notes_manager,
    dispatcher=dispatcher,
)
ctx.launcher = Launcher(ctx)

# Главное окно, меню трея и лаунчер строятся из одного списка модулей (modules.py)
MODULES = build_modules()

tray_actions = [
    (module.title, lambda module=module: module.run(ctx))
    for module in MODULES
    if module.tray
]

tray = Tray(root, dispatcher, actions=tray_actions)
ctx.tray = tray

# ---------------------------------------------------------
# Глобальная горячая клавиша лаунчера
# ---------------------------------------------------------

hotkey = GlobalHotkey()
hotkey_spec = BASE_SETTINGS.get("BASE", {}).get("hotkey", "ctrl+space")

# в ini можно написать hotkey = off (читается как False), чтобы отключить
if hotkey_spec and str(hotkey_spec).lower() not in ("off", "none", "false"):
    if not hotkey.start(str(hotkey_spec), lambda: dispatcher.call(ctx.launcher.toggle)):
        problems.append(f"Hotkey: {hotkey.error}")

# ---------------------------------------------------------
# UI
# ---------------------------------------------------------

label = tk.Label(root, text="Greetings!")
label.pack(pady=10)

if problems:
    tk.Label(
        root,
        text="⚠ " + "\n".join(problems),
        fg="red", font=("Arial", 8), justify="left",
    ).pack(pady=(0, 5))

for module in MODULES:
    tk.Button(
        root,
        text=module.title,
        command=lambda module=module: module.run(ctx),
    ).pack(
        fill="x",
        padx=10,
        pady=5,
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
    hotkey.stop()
    tray.stop()
    instance.close()
