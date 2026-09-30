from dataclasses import dataclass
from pathlib import Path

from scripts.note_manager import NotesManager
from scripts.quick_commands_manager import QuickCommandsManager


@dataclass
class ToolkitContext:
    base_dir: Path
    settings: dict
    notes_manager: NotesManager
    quick_commands_manager: QuickCommandsManager