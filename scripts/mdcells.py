"""
Markdown <-> cells. A "cell" is one block of a note: a line of text, a heading, one list item,
a fenced code block, a table, a quote. Pure functions, no UI.

    split_cells(body)   -> list[str]     file text -> cells
    join_cells(cells)   -> str           cells -> file text (what is written to the .md file)

The editor writes cells separated by a blank line (list items of one list are kept together),
so what you typed comes back as the same cells. A note written by hand (VS Code, Obsidian)
is split by the same rules: a paragraph stays ONE cell, every list item / heading is its own.
"""
from __future__ import annotations

import re

LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+")
TASK_RE = re.compile(r"^(\s*)([-*+])\s+\[( |x|X)\]\s?(.*)$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^#{1,6}\s")
RULE_RE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
TABLE_RE = re.compile(r"^\s*\|")
QUOTE_RE = re.compile(r"^\s*>")


def is_list_item(text: str) -> bool:
    return bool(LIST_RE.match(text.split("\n", 1)[0]))


def is_open_fence(text: str) -> bool:
    """True while a ``` block in this cell is not closed yet (Enter must add a line, not a cell)."""
    fences = [m.group(1) for line in text.split("\n") if (m := FENCE_RE.match(line))]
    return len(fences) % 2 == 1


def next_prefix(text: str) -> str | None:
    """
    Prefix for the cell created after this one by Enter: keeps a list going.
        "- a" -> "- ",  "3. a" -> "4. ",  "- [x] a" -> "- [ ] ".
    None when the cell is not a list item; "" when the item is empty (Enter ends the list).
    """
    first = text.split("\n", 1)[0]
    task = TASK_RE.match(first)
    if task:
        return "" if not task.group(4).strip() else f"{task.group(1)}{task.group(2)} [ ] "

    m = LIST_RE.match(first)
    if not m:
        return None
    if not first[m.end():].strip():
        return ""

    marker = m.group(2)
    if marker[:-1].isdigit():
        return f"{m.group(1)}{int(marker[:-1]) + 1}{marker[-1]} "
    return f"{m.group(1)}{marker} "


def _paragraph_to_cells(lines: list[str]) -> list[str]:
    cells: list[str] = []
    kind = None                      # what the last cell is: "text" | "item" | "table" | "quote"
    for line in lines:
        if HEADING_RE.match(line) or RULE_RE.match(line):
            cells.append(line)
            kind = None
        elif LIST_RE.match(line):
            cells.append(line)
            kind = "item"
        elif TABLE_RE.match(line):
            if kind == "table":
                cells[-1] += "\n" + line
            else:
                cells.append(line)
                kind = "table"
        elif QUOTE_RE.match(line):
            if kind == "quote":
                cells[-1] += "\n" + line
            else:
                cells.append(line)
                kind = "quote"
        elif kind == "item" and line[:1] in (" ", "\t"):
            cells[-1] += "\n" + line                      # continuation of a list item
        elif kind == "text":
            cells[-1] += "\n" + line                      # wrapped paragraph = one cell
        else:
            cells.append(line)
            kind = "text"
    return cells


def split_cells(body: str) -> list[str]:
    cells: list[str] = []
    paragraph: list[str] = []
    fence: str | None = None
    fence_lines: list[str] = []

    def flush() -> None:
        if paragraph:
            cells.extend(_paragraph_to_cells(paragraph))
            paragraph.clear()

    for line in body.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if fence is not None:
            fence_lines.append(line)
            if line.strip().startswith(fence):
                cells.append("\n".join(fence_lines))
                fence, fence_lines = None, []
            continue

        opened = FENCE_RE.match(line)
        if opened:
            flush()
            fence, fence_lines = opened.group(1), [line]
        elif not line.strip():
            flush()
        else:
            paragraph.append(line.rstrip())

    flush()
    if fence is not None:                                   # unclosed fence: keep what there is
        cells.append("\n".join(fence_lines))
    return cells


def join_cells(cells) -> str:
    out: list[str] = []
    previous = None
    for cell in cells:
        cell = cell.strip("\n").rstrip()
        if not cell.strip():
            continue
        if previous is not None:
            both_items = is_list_item(previous) and is_list_item(cell)
            out.append("\n" if both_items else "\n\n")
        out.append(cell)
        previous = cell
    return "".join(out) + ("\n" if out else "")


def plain_to_markdown(text: str) -> str:
    """
    Old plain-text notes -> markdown. Indentation would turn into code blocks, so it is dropped;
    "1)" becomes "1."; every line becomes a cell (that is how the old notes were written).
    """
    cells = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^(\d+)\)\s+", r"\1. ", line)
        line = re.sub(r"^[•·–—]\s+", "- ", line)
        cells.append(line)
    return join_cells(cells)
