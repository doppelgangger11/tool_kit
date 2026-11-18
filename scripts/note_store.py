"""
Notes as markdown files: one note = one .md file in <notes_dir>/notes/.

    ---
    title: Meeting
    created: 2026-09-22 13:59:16
    pinned: true
    ---
    # Heading
    text ...

Any other front matter lines (tags, aliases, ...) are kept as they are, so a note edited in
Obsidian / VS Code keeps its metadata. Files without front matter work too.
Deleting moves the file to notes/.trash/. No UI code here.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .mdcells import plain_to_markdown

DATE_FMT = "%Y-%m-%d %H:%M:%S"
IMPORT_MARKER = ".imported"


@dataclass
class Note:
    id: str                                  # file name without .md
    title: str = ""
    body: str = ""
    created: str = ""
    pinned: bool = False
    updated: float = 0.0                     # file mtime
    extra: list[str] = field(default_factory=list)      # unknown front-matter lines, kept verbatim

    @property
    def display_title(self) -> str:
        return self.title.strip() or "Untitled"

    def preview(self, limit: int = 70) -> str:
        for line in self.body.splitlines():
            clean = re.sub(r"^[#>\-\*\+\s\d\.\)\[\]xX]+", "", line).strip()
            if clean:
                return clean[:limit]
        return ""


def _slug(text: str) -> str:
    slug = re.sub(r"[^\w-]+", "-", text.lower(), flags=re.UNICODE).strip("-_")
    return slug[:40] or "note"


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1].replace('\\"', '"')
    return value


def _quote(value: str) -> str:
    if value[:1] in "\"'[{#&*!|>%@`" or value != value.strip():
        return '"' + value.replace('"', '\\"') + '"'
    return value


def parse(text: str) -> tuple[dict, list[str], str]:
    """-> (known keys, other front-matter lines, body)"""
    text = text.replace("\r\n", "\n")
    meta: dict = {}
    extra: list[str] = []

    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1 and text[end + 4:end + 5] in ("", "\n"):
            for line in text[4:end].split("\n"):
                key, sep, value = line.partition(":")
                key = key.strip().lower()
                if sep and key in ("title", "created", "pinned") and not line.startswith((" ", "\t")):
                    meta[key] = _unquote(value)
                elif line.strip():
                    extra.append(line)
            return meta, extra, text[end + 5:].lstrip("\n")
    return meta, extra, text


def render(note: Note) -> str:
    lines = ["---", f"title: {_quote(note.title)}", f"created: {note.created}"]
    if note.pinned:
        lines.append("pinned: true")
    lines.extend(note.extra)
    lines.append("---")
    return "\n".join(lines) + "\n" + note.body.lstrip("\n")


class NoteStore:
    def __init__(self, directory: Path):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    # ---- reading ----

    def path(self, note_or_id) -> Path:
        note_id = note_or_id.id if isinstance(note_or_id, Note) else note_or_id
        return self.dir / f"{note_id}.md"

    def _read(self, path: Path) -> Note:
        text = path.read_text(encoding="utf-8", errors="replace")
        meta, extra, body = parse(text)
        stat = path.stat()

        title = meta.get("title")
        if title is None:
            heading = re.match(r"#\s+(.+)", body)
            title = heading.group(1).strip() if heading else path.stem

        created = meta.get("created") or datetime.fromtimestamp(stat.st_ctime).strftime(DATE_FMT)
        return Note(path.stem, title, body, created,
                    meta.get("pinned", "").lower() in ("true", "yes", "1"), stat.st_mtime, extra)

    def get(self, note_id: str) -> Note | None:
        path = self.path(note_id)
        return self._read(path) if path.exists() else None

    def reload(self, note: Note) -> Note | None:
        return self.get(note.id)

    def list(self, query: str = "") -> list[Note]:
        notes = []
        for path in self.dir.glob("*.md"):
            if path.name.startswith("."):
                continue
            try:
                notes.append(self._read(path))
            except OSError:
                continue

        query = query.strip().lower()
        if query:
            notes = [n for n in notes if query in n.title.lower() or query in n.body.lower()]

        notes.sort(key=lambda n: (not n.pinned, -n.updated))
        return notes

    # ---- writing ----

    def create(self, title: str = "", body: str = "", created: datetime | None = None,
               pinned: bool = False) -> Note:
        created = created or datetime.now().replace(microsecond=0)
        base = f"{created:%Y%m%d-%H%M%S}-{_slug(title)}"
        note_id, n = base, 2
        while self.path(note_id).exists():
            note_id, n = f"{base}-{n}", n + 1

        note = Note(note_id, title, body, created.strftime(DATE_FMT), pinned)
        self.save(note)
        return note

    def save(self, note: Note) -> None:
        path = self.path(note)
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(render(note), encoding="utf-8")
        tmp.replace(path)
        note.updated = path.stat().st_mtime

    def delete(self, note: Note) -> Path:
        trash = self.dir / ".trash"
        trash.mkdir(exist_ok=True)
        target = trash / f"{int(time.time())}-{note.id}.md"
        shutil.move(str(self.path(note)), str(target))
        return target

    # ---- one-time import of the old notes.json ----

    def import_legacy_json(self, json_path: Path) -> int:
        """Convert notes.json once. The json file is left untouched. Returns how many were imported."""
        marker = self.dir / IMPORT_MARKER
        json_path = Path(json_path)
        if marker.exists() or not json_path.exists():
            return 0

        try:
            items = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return 0

        count = 0
        for item in items if isinstance(items, list) else []:
            try:
                created = datetime.strptime(item["date"], DATE_FMT)
            except (KeyError, ValueError):
                created = datetime.now().replace(microsecond=0)
            note = self.create(str(item.get("theme", "")), plain_to_markdown(str(item.get("note", ""))),
                               created, bool(item.get("pinned", False)))
            stamp = created.timestamp()                       # keep the original date as file date
            os.utime(self.path(note), (stamp, stamp))
            count += 1

        marker.write_text(f"imported {count} notes from {json_path.name}\n", encoding="utf-8")
        return count
