from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class AppContext:
    """Everything the utilities need in one object instead of argument tuples."""
    root: Any
    base_dir: Path
    settings: dict
    notes_manager: Any
    dispatcher: Any = None
    tray: Any = None
    launcher: Any = None
    todos: Any = None          # TodoManager
    todo_quick: Any = None     # QuickAdd popup


@dataclass(frozen=True)
class Module:
    key: str
    title: str
    action: Callable[[AppContext], None]
    tray: bool = False            # show in the tray menu
    in_launcher: bool = True      # search in the launcher
    keywords: tuple[str, ...] = field(default_factory=tuple)  # additional search terms

    def run(self, ctx: AppContext) -> None:
        self.action(ctx)
