"""
Todo storage and quick-input parsing (no GUI, easy to test).

Quick input understands a few tokens anywhere in the text:

    buy milk #home !! @tomorrow

    #tag            a tag (several allowed)
    !  !!  !!!      priority 1..3 (a separate word)
    @today @tomorrow @mon..@sun @2026-11-05 @5.11 @+3d @2w
                    due date (Russian words work too: @завтра @пт)

Unknown @words stay in the text untouched.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable

MAX_UNDO = 100

WEEKDAYS = {
    "mon": 0, "monday": 0, "пн": 0, "понедельник": 0,
    "tue": 1, "tues": 1, "tuesday": 1, "вт": 1, "вторник": 1,
    "wed": 2, "wednesday": 2, "ср": 2, "среда": 2,
    "thu": 3, "thur": 3, "thurs": 3, "thursday": 3, "чт": 3, "четверг": 3,
    "fri": 4, "friday": 4, "пт": 4, "пятница": 4,
    "sat": 5, "saturday": 5, "сб": 5, "суббота": 5,
    "sun": 6, "sunday": 6, "вс": 6, "воскресенье": 6,
}

RELATIVE_DAYS = {
    "today": 0, "сегодня": 0,
    "tomorrow": 1, "tmr": 1, "завтра": 1,
    "послезавтра": 2,
}

WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

_TAG = re.compile(r"#([\w\-]+)", re.UNICODE)
_PRIORITY = re.compile(r"!{1,3}")
_OFFSET = re.compile(r"\+?(\d{1,3})([dwдн])")
_ISO = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
_DMY = re.compile(r"(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?")
# "- ", "* ", "• ", "[ ] ", "1. " at the start of a pasted line
_LIST_MARKER = re.compile(r"^\s*(?:[-*•–]|\[[ xX]?\]|\d+[.)])\s+")


# ---------------------------------------------------------
# parsing
# ---------------------------------------------------------

def parse_due(word: str, today: date | None = None) -> date | None:
    """'tomorrow', 'fri', '5.11', '2026-11-05', '+3d' -> date, or None."""
    today = today or date.today()
    word = word.strip().lower()

    if not word:
        return None

    if word in RELATIVE_DAYS:
        return today + timedelta(days=RELATIVE_DAYS[word])

    if word in WEEKDAYS:
        delta = (WEEKDAYS[word] - today.weekday()) % 7 or 7
        return today + timedelta(days=delta)

    match = _OFFSET.fullmatch(word)

    if match:
        amount = int(match.group(1))
        unit = match.group(2)

        return today + timedelta(days=amount * (7 if unit in "wн" else 1))

    try:
        match = _ISO.fullmatch(word)

        if match:
            return date(*(int(part) for part in match.groups()))

        match = _DMY.fullmatch(word)

        if match:
            day, month = int(match.group(1)), int(match.group(2))
            year = match.group(3)

            if year:
                year = int(year)
                year += 2000 if year < 100 else 0

                return date(year, month, day)

            result = date(today.year, month, day)

            # "@5.11" typed in December means next year
            if result < today:
                result = date(today.year + 1, month, day)

            return result

    except ValueError:
        return None

    return None


def parse_quick(raw: str, today: date | None = None) -> dict | None:
    """
    Splits quick input into text, tags, priority and due date.
    Returns None when nothing is left of the text.
    """
    today = today or date.today()

    kept = []
    tags = []
    priority = 0
    due = None

    for word in raw.split():

        if _PRIORITY.fullmatch(word):
            priority = len(word)
            continue

        tag = _TAG.fullmatch(word)

        if tag:
            name = tag.group(1).lower()

            if name not in tags:
                tags.append(name)

            continue

        if word.startswith("@") and len(word) > 1:
            parsed = parse_due(word[1:], today)

            if parsed is not None:
                due = parsed
                continue

        kept.append(word)

    text = " ".join(kept).strip()

    if not text:
        return None

    return {
        "text": text,
        "tags": tags,
        "priority": priority,
        "due": due.isoformat() if due else None,
    }


def format_due(due: str | None, today: date | None = None) -> tuple[str, bool]:
    """
    ISO date -> (short label, is_overdue).
    """
    if not due:
        return "", False

    today = today or date.today()

    try:
        day = date.fromisoformat(due)
    except ValueError:
        return due, False

    delta = (day - today).days

    if delta == 0:
        return "Today", False

    if delta == 1:
        return "Tomorrow", False

    if delta == -1:
        return "Yesterday", True

    if delta < 0:
        return f"{day.day} {day.strftime('%b')}", True

    if delta < 7:
        return WEEKDAY_NAMES[day.weekday()], False

    return f"{day.day} {day.strftime('%b')}", False


# ---------------------------------------------------------
# model
# ---------------------------------------------------------

@dataclass
class Todo:
    id: str
    text: str
    done: bool = False
    created: str = ""
    done_at: str | None = None
    priority: int = 0
    due: str | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "done": self.done,
            "created": self.created,
            "done_at": self.done_at,
            "priority": self.priority,
            "due": self.due,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Todo":
        return cls(
            id=str(data.get("id") or uuid.uuid4().hex[:8]),
            text=str(data.get("text", "")),
            done=bool(data.get("done", False)),
            created=str(data.get("created") or ""),
            done_at=data.get("done_at"),
            priority=max(0, min(3, int(data.get("priority", 0) or 0))),
            due=data.get("due") or None,
            tags=[str(tag) for tag in data.get("tags", [])],
        )

    def raw(self) -> str:
        """Text in the quick-input syntax (used for editing)."""
        parts = [self.text]

        parts.extend(f"#{tag}" for tag in self.tags)

        if self.priority:
            parts.append("!" * self.priority)

        if self.due:
            parts.append(f"@{self.due}")

        return " ".join(parts)


def _now() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


# ---------------------------------------------------------
# manager
# ---------------------------------------------------------

class TodoManager:
    """
    Keeps the todo list in a JSON file. Every change is saved at once
    (atomically) and can be undone.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.todos: list[Todo] = []
        self.load_error: str | None = None

        self._undo: list[list[dict]] = []
        self._listeners: list[Callable[[], None]] = []

        self.load()

    # ----- storage -----

    def load(self) -> None:
        self.todos = []
        self.load_error = None

        if not self.path.is_file():
            return

        try:
            with self.path.open("r", encoding="utf-8-sig") as file:
                data = json.load(file)

            if not isinstance(data, list):
                raise ValueError("expected a list")

            self.todos = [Todo.from_dict(item) for item in data]

        except (OSError, ValueError, TypeError, AttributeError) as error:
            backup = self.path.with_name(self.path.name + ".bak")

            self.load_error = f"{self.path.name} is broken ({error}), copy: {backup.name}"

            try:
                os.replace(self.path, backup)
            except OSError:
                pass

            self.todos = []

    def save(self) -> bool:
        tmp = self.path.with_name(self.path.name + ".tmp")

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)

            with tmp.open("w", encoding="utf-8") as file:
                json.dump(
                    [todo.to_dict() for todo in self.todos],
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

            os.replace(tmp, self.path)

            return True

        except OSError as error:
            print(f"[Todo] Cannot save {self.path}: {error}")

            return False

    # ----- observers -----

    def subscribe(self, callback: Callable[[], None]) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unsubscribe(self, callback: Callable[[], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _changed(self) -> None:
        self.save()

        for callback in list(self._listeners):
            try:
                callback()
            except Exception as error:
                print(f"[Todo] listener error: {error!r}")

    def _snapshot(self) -> None:
        self._undo.append([todo.to_dict() for todo in self.todos])

        if len(self._undo) > MAX_UNDO:
            del self._undo[0]

    def undo(self) -> bool:
        if not self._undo:
            return False

        self.todos = [Todo.from_dict(item) for item in self._undo.pop()]

        self._changed()

        return True

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    # ----- queries -----

    def get(self, todo_id: str) -> Todo | None:
        for todo in self.todos:
            if todo.id == todo_id:
                return todo

        return None

    def counts(self) -> dict[str, int]:
        done = sum(1 for todo in self.todos if todo.done)

        return {
            "active": len(self.todos) - done,
            "done": done,
        }

    def tags(self) -> list[str]:
        return sorted({tag for todo in self.todos for tag in todo.tags})

    def view(
        self,
        mode: str = "active",
        tag: str | None = None,
        search: str = "",
    ) -> list[Todo]:
        """
        Todos for display. mode: "active", "all" or "done".

        Order: unfinished first by priority (high first), then by due date,
        then by creation order; finished ones last, most recent first.
        """
        search = search.strip().lower()

        items = []

        for todo in self.todos:
            if mode == "active" and todo.done:
                continue

            if mode == "done" and not todo.done:
                continue

            if tag and tag not in todo.tags:
                continue

            if search:
                haystack = todo.text.lower() + " " + " ".join(todo.tags)

                if search not in haystack:
                    continue

            items.append(todo)

        order = {todo.id: index for index, todo in enumerate(self.todos)}

        active = sorted(
            (todo for todo in items if not todo.done),
            key=lambda todo: (
                -todo.priority,
                todo.due or "9999-99-99",
                order[todo.id],
            ),
        )

        finished = sorted(
            (todo for todo in items if todo.done),
            key=lambda todo: todo.done_at or "",
            reverse=True,
        )

        return active + finished

    # ----- changes -----

    def _make(self, raw: str, today: date | None = None) -> Todo | None:
        parsed = parse_quick(_LIST_MARKER.sub("", raw), today)

        if parsed is None:
            return None

        return Todo(
            id=uuid.uuid4().hex[:8],
            created=_now(),
            **parsed,
        )

    def add(self, raw: str, today: date | None = None) -> Todo | None:
        return (self.add_many([raw], today) or [None])[0]

    def add_many(self, lines: Iterable[str], today: date | None = None) -> list[Todo]:
        """Adds one todo per non-empty line; a single undo reverts all of them."""
        created = []

        for line in lines:
            todo = self._make(line, today)

            if todo is not None:
                created.append(todo)

        if not created:
            return []

        self._snapshot()
        self.todos.extend(created)
        self._changed()

        return created

    def toggle(self, ids: Iterable[str]) -> None:
        """
        Marks the todos done; if all of them are already done, reopens them.
        """
        targets = [todo for todo in self.todos if todo.id in set(ids)]

        if not targets:
            return

        make_done = any(not todo.done for todo in targets)

        self._snapshot()

        for todo in targets:
            todo.done = make_done
            todo.done_at = _now() if make_done else None

        self._changed()

    def update(self, todo_id: str, raw: str, today: date | None = None) -> bool:
        todo = self.get(todo_id)
        parsed = parse_quick(raw, today)

        if todo is None or parsed is None:
            return False

        if (
            parsed["text"] == todo.text
            and parsed["tags"] == todo.tags
            and parsed["priority"] == todo.priority
            and parsed["due"] == todo.due
        ):
            return True

        self._snapshot()

        todo.text = parsed["text"]
        todo.tags = parsed["tags"]
        todo.priority = parsed["priority"]
        todo.due = parsed["due"]

        self._changed()

        return True

    def set_priority(self, ids: Iterable[str], priority: int) -> None:
        targets = [todo for todo in self.todos if todo.id in set(ids)]

        if not targets:
            return

        self._snapshot()

        for todo in targets:
            todo.priority = max(0, min(3, priority))

        self._changed()

    def set_due(self, ids: Iterable[str], due: date | None) -> None:
        targets = [todo for todo in self.todos if todo.id in set(ids)]

        if not targets:
            return

        self._snapshot()

        for todo in targets:
            todo.due = due.isoformat() if due else None

        self._changed()

    def delete(self, ids: Iterable[str]) -> int:
        ids = set(ids)
        keep = [todo for todo in self.todos if todo.id not in ids]
        removed = len(self.todos) - len(keep)

        if not removed:
            return 0

        self._snapshot()
        self.todos = keep
        self._changed()

        return removed

    def clear_done(self) -> int:
        return self.delete(todo.id for todo in self.todos if todo.done)
