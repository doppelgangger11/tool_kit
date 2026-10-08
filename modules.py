"""
List of Toolkit utilities. To add a new one, add a Module to build_modules().
Heavy modules (games) are imported lazily, on first click.
"""
from scripts.registry import Module


def _launch_work_setup(ctx):
    from scripts.program_launcher import launch_selected_programs
    launch_selected_programs(ctx.settings)


def _activation(ctx):
    from interface.open_activation_window import open_activation
    open_activation(ctx.root, ctx.base_dir, ctx.settings)


def _notes(ctx):
    from interface.quick_notes_window import open_notes
    open_notes(ctx.root, ctx.notes_manager)


def _quick_commands(ctx):
    from interface.quick_commands_window import open_quick_commands
    open_quick_commands(ctx.root, ctx.base_dir, ctx.settings)


def _chess(ctx):
    from games.chess.chess_interface import main
    main()


def _minesweeper(ctx):
    from games.minesweeper.main import main
    main()


def _tic_tac_toe(ctx):
    from games.tic_tac_toe.main import main
    main()


def _settings(ctx):
    from interface.open_settings_window import open_settings
    open_settings(ctx.root, ctx.base_dir, ctx.settings)


def build_modules() -> list[Module]:
    return [
        Module("search", "Search / Launcher", lambda c: c.launcher.toggle(),
               tray=True, in_launcher=False),
        Module("launcher", "Launch work setup", _launch_work_setup,
               tray=True, keywords=("work", "programs", "старт", "программы")),
        Module("activation", "Activate new task", _activation,
               tray=True, keywords=("task", "project", "задача", "проект")),
        Module("notes", "Quick Notes", _notes,
               tray=True, keywords=("notes", "заметки")),
        Module("quick_commands", "Quick Commands", _quick_commands,
               tray=True, keywords=("git", "cmd", "команды")),
        Module("chess", "Chess", _chess, keywords=("шахматы", "game")),
        Module("minesweeper", "Minesweeper", _minesweeper, keywords=("сапёр", "сапер", "game")),
        Module("tic_tac_toe", "Tic-Tac-Toe", _tic_tac_toe, keywords=("крестики", "game")),
        Module("settings", "Settings", _settings, keywords=("настройки", "config")),
        Module("exit", "Exit", lambda c: c.root.destroy(), in_launcher=False),
    ]
