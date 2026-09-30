from pathlib import Path
from initializer import initialize

from scripts.note_manager import NotesManager
from scripts.quick_commands_manager import QuickCommandsManager
from scripts.settings_manager import read_settings

from interface.app import ToolkitApp
from interface.context import ToolkitContext

from interface.views.dashboard import DashboardView
from interface.views.launcher import LauncherView
from interface.views.activation import ActivationView
from interface.views.notes import NotesView
from interface.views.quick_commands import QuickCommandsView


initialize()

BASE_DIR = Path('./')

settings = read_settings((BASE_DIR / "db"))

notes_manager = NotesManager(
    path=BASE_DIR / "db" / "notes.json"
)
notes_manager.read_notes()

quick_commands_manager = QuickCommandsManager(
    path=BASE_DIR / "db" / "quick_commands.ini"
)

context = ToolkitContext(
    base_dir=BASE_DIR,
    settings=settings,
    notes_manager=notes_manager,
    quick_commands_manager=quick_commands_manager,
)

app = ToolkitApp(context)


app.register(
    id="dashboard",
    title="Dashboard",
    icon="⌂",
    group="MAIN",
    view=DashboardView,
)

app.register(
    id="launcher",
    title="Launcher",
    icon="🚀",
    group="WORK",
    view=LauncherView,
)

app.register(
    id="activation",
    title="New Task",
    icon="⚡",
    group="WORK",
    view=ActivationView,
)

app.register(
    id="notes",
    title="Quick Notes",
    icon="📝",
    group="TOOLS",
    view=NotesView,
)

app.register(
    id="commands",
    title="Quick Commands",
    icon="⌨",
    group="TOOLS",
    view=QuickCommandsView,
)

app.show("dashboard")

app.mainloop()