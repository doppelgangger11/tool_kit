from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class AppContext:
    """Всё, что нужно утилитам, в одном объекте вместо кортежей аргументов."""
    root: Any
    base_dir: Path
    settings: dict
    notes_manager: Any
    dispatcher: Any = None
    tray: Any = None
    launcher: Any = None


@dataclass(frozen=True)
class Module:
    key: str
    title: str
    action: Callable[[AppContext], None]
    tray: bool = False            # показывать в меню трея
    in_launcher: bool = True      # искать в лаунчере
    keywords: tuple[str, ...] = field(default_factory=tuple)  # доп. слова для поиска

    def run(self, ctx: AppContext) -> None:
        self.action(ctx)
