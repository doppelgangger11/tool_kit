from __future__ import annotations

import json
import random
import sys
import tkinter as tk

from pathlib import Path
from tkinter import messagebox, ttk
from typing import NamedTuple


# ============================================================
# FIELD RULES
# ============================================================

MIN_SIDE = 5
MAX_ROWS = 30
MAX_COLS = 50
SAFE_ZONE = 9            # first click and its neighbours never contain mines

PRESETS = {
    "Beginner  9×9, 10 mines": (9, 9, 10),
    "Intermediate  16×16, 40 mines": (16, 16, 40),
    "Expert  16×30, 99 mines": (16, 30, 99),
    "Large  20×20, 70 mines": (20, 20, 70),
}

DEFAULT_FIELD = (20, 20, 70)     # same as the original game


def validate_field(rows: int, cols: int, mines: int) -> str | None:
    """Returns an error text or None if the field is fine."""
    if not MIN_SIDE <= rows <= MAX_ROWS:
        return f"Height must be between {MIN_SIDE} and {MAX_ROWS}."

    if not MIN_SIDE <= cols <= MAX_COLS:
        return f"Width must be between {MIN_SIDE} and {MAX_COLS}."

    limit = rows * cols - SAFE_ZONE

    if not 1 <= mines <= limit:
        return f"Mines must be between 1 and {limit} for this size."

    return None


# ============================================================
# ENGINE (no Tk: easy to test)
# ============================================================

class Changes(NamedTuple):
    revealed: list
    flagged: list
    unflagged: list
    exploded: tuple | None = None


def _no_changes() -> Changes:
    return Changes([], [], [])


class Board:
    """
    state: ready   - nothing opened yet (mines are placed on the first click)
           playing
           won
           lost
    """

    def __init__(self, rows, cols, mines, fixed_mines=None, rng=None):
        self.rows = rows
        self.cols = cols
        self.mine_count = mines
        self.rng = rng or random.Random()

        self.mines: set = set()
        self.numbers = [[0] * cols for _ in range(rows)]
        self.revealed: set = set()
        self.flags: set = set()
        self.state = "ready"

        if fixed_mines is not None:          # for tests
            self.mines = set(fixed_mines)
            self.mine_count = len(self.mines)
            self._count_numbers()
            self.state = "playing"

    # ---- helpers ----

    def neighbors(self, row, col):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr or dc:
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        yield nr, nc

    @property
    def remaining(self) -> int:
        return self.mine_count - len(self.flags)

    def hidden_mines(self) -> set:
        return self.mines - self.flags

    def wrong_flags(self) -> set:
        return self.flags - self.mines

    def _count_numbers(self):
        self.numbers = [[0] * self.cols for _ in range(self.rows)]
        for r, c in self.mines:
            for nr, nc in self.neighbors(r, c):
                self.numbers[nr][nc] += 1

    def _place_mines(self, safe_row, safe_col):
        forbidden = {(safe_row, safe_col), *self.neighbors(safe_row, safe_col)}
        cells = [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if (r, c) not in forbidden
        ]
        self.mines = set(
            self.rng.sample(cells, min(self.mine_count, len(cells)))
        )
        self._count_numbers()

    def _flood(self, row, col, changes):
        """Opens a cell; empty cells open their neighbours (no recursion)."""
        stack = [(row, col)]

        while stack:
            cell = stack.pop()

            if cell in self.revealed or cell in self.flags:
                continue

            self.revealed.add(cell)
            changes.revealed.append(cell)

            if self.numbers[cell[0]][cell[1]] == 0:
                stack.extend(
                    p for p in self.neighbors(*cell)
                    if p not in self.revealed and p not in self.flags
                )

    def _check_win(self, changes):
        if len(self.revealed) == self.rows * self.cols - len(self.mines):
            self.state = "won"

            for cell in self.mines - self.flags:
                self.flags.add(cell)
                changes.flagged.append(cell)

    def _lose(self, cell) -> Changes:
        self.state = "lost"
        return Changes([], [], [], cell)

    # ---- actions ----

    def open_cell(self, row, col) -> Changes:
        cell = (row, col)

        if self.state in ("won", "lost") or cell in self.flags or cell in self.revealed:
            return _no_changes()

        if self.state == "ready":
            self._place_mines(row, col)
            self.state = "playing"

        if cell in self.mines:
            return self._lose(cell)

        changes = _no_changes()
        self._flood(row, col, changes)
        self._check_win(changes)
        return changes

    def toggle_flag(self, row, col) -> Changes:
        cell = (row, col)

        if self.state in ("won", "lost") or cell in self.revealed:
            return _no_changes()

        changes = _no_changes()

        if cell in self.flags:
            self.flags.remove(cell)
            changes.unflagged.append(cell)
        else:
            self.flags.add(cell)
            changes.flagged.append(cell)

        return changes

    def chord(self, row, col) -> Changes:
        """
        Click on an opened number: if exactly that many flags stand around it,
        open every other neighbour. A wrong flag makes this a mine hit.
        """
        cell = (row, col)

        if self.state != "playing" or cell not in self.revealed:
            return _no_changes()

        number = self.numbers[row][col]
        around = list(self.neighbors(row, col))

        if number == 0 or sum(p in self.flags for p in around) != number:
            return _no_changes()

        targets = [p for p in around if p not in self.flags and p not in self.revealed]

        if not targets:
            return _no_changes()

        hit = next((p for p in targets if p in self.mines), None)
        if hit:
            return self._lose(hit)

        changes = _no_changes()
        for p in targets:
            self._flood(*p, changes)

        self._check_win(changes)
        return changes

    def auto_flag(self, row, col) -> Changes:
        """
        Right click on an opened number: if the number of still closed
        neighbours (flagged ones included) equals the number, all of them
        are mines, so flag them.
        """
        cell = (row, col)

        if self.state != "playing" or cell not in self.revealed:
            return _no_changes()

        number = self.numbers[row][col]
        closed = [p for p in self.neighbors(row, col) if p not in self.revealed]

        if number == 0 or len(closed) != number:
            return _no_changes()

        changes = _no_changes()

        for p in closed:
            if p not in self.flags:
                self.flags.add(p)
                changes.flagged.append(p)

        return changes


# ============================================================
# UI
# ============================================================

NUMBER_COLORS = {
    1: "blue", 2: "green", 3: "red", 4: "purple",
    5: "maroon", 6: "turquoise", 7: "black", 8: "gray",
}

HIDDEN_BG = "#d1d1d1"
OPEN_BG = "#e1e1e1"

_MAC = sys.platform == "darwin"
RIGHT_CLICK = "<Button-2>" if _MAC else "<Button-3>"
MIDDLE_CLICK = "<Button-3>" if _MAC else "<Button-2>"


class Minesweeper:
    def __init__(self, window, storage_path=None):
        self.window = window
        self.storage_path = Path(storage_path) if storage_path else None

        self.alive = True
        self.board: Board | None = None
        self.cells: dict = {}
        self.grid_size = None
        self.seconds = 0
        self.timer_job = None

        settings = self._load_settings()
        self.rows, self.cols, self.mines = settings["field"]

        self.chord_var = tk.BooleanVar(master=window, value=settings["chord"])
        self.auto_flag_var = tk.BooleanVar(master=window, value=settings["auto_flag"])
        self.preset_var = tk.StringVar(master=window)
        self.status_var = tk.StringVar(master=window)

        window.title("Minesweeper")
        window.resizable(False, False)
        window.protocol("WM_DELETE_WINDOW", self.close)
        window.bind("<F2>", lambda event: self.new_game())

        self._build_menu()
        self._build_header()

        self.board_frame = tk.Frame(window, bd=2, relief="sunken")
        self.board_frame.pack(padx=8, pady=(0, 4))

        tk.Label(
            window, textvariable=self.status_var, fg="#444444",
            font=("Arial", 9),
        ).pack(pady=(0, 8))

        self.new_game()

    # --------------------------------------------------
    # SETTINGS
    # --------------------------------------------------

    def _load_settings(self) -> dict:
        data = {}

        if self.storage_path:
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}

        field = DEFAULT_FIELD
        try:
            candidate = (int(data["rows"]), int(data["cols"]), int(data["mines"]))
            if validate_field(*candidate) is None:
                field = candidate
        except (KeyError, TypeError, ValueError):
            pass

        return {
            "field": field,
            "chord": bool(data.get("chord", True)),
            "auto_flag": bool(data.get("auto_flag", True)),
        }

    def _save_settings(self):
        if not self.storage_path:
            return

        data = {
            "rows": self.rows, "cols": self.cols, "mines": self.mines,
            "chord": self.chord_var.get(),
            "auto_flag": self.auto_flag_var.get(),
        }

        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    # --------------------------------------------------
    # MENU / HEADER
    # --------------------------------------------------

    def _build_menu(self):
        menubar = tk.Menu(self.window)

        game = tk.Menu(menubar, tearoff=False)
        game.add_command(label="New game", accelerator="F2", command=self.new_game)
        game.add_separator()

        for name, field in PRESETS.items():
            game.add_radiobutton(
                label=name, variable=self.preset_var, value=name,
                command=lambda f=field: self._set_field(*f),
            )

        game.add_radiobutton(
            label="Custom…", variable=self.preset_var, value="Custom",
            command=self._custom_dialog,
        )
        game.add_separator()
        game.add_command(label="Exit", command=self.close)
        menubar.add_cascade(label="Game", menu=game)

        options = tk.Menu(menubar, tearoff=False)
        options.add_checkbutton(
            label="Click a number to open its neighbours",
            variable=self.chord_var, command=self._save_settings,
        )
        options.add_checkbutton(
            label="Right-click a number to flag obvious mines",
            variable=self.auto_flag_var, command=self._save_settings,
        )
        menubar.add_cascade(label="Options", menu=options)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Controls", command=self._show_help)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.window.config(menu=menubar)

    def _build_header(self):
        header = tk.Frame(self.window, padx=8, pady=6)
        header.pack(fill="x")
        header.columnconfigure(1, weight=1)

        counter_style = dict(
            font=("Consolas", 16, "bold"), fg="#ff3b30", bg="black",
            width=4, padx=4,
        )

        self.counter_label = tk.Label(header, text="000", **counter_style)
        self.counter_label.grid(row=0, column=0)

        self.smiley = tk.Button(
            header, text="🙂", font=("Arial", 14), width=3,
            command=self.new_game,
        )
        self.smiley.grid(row=0, column=1)

        self.timer_label = tk.Label(header, text="000", **counter_style)
        self.timer_label.grid(row=0, column=2)

    def _show_help(self):
        messagebox.showinfo(
            "Controls",
            "Left click on a closed cell: open it\n"
            "Right click on a closed cell: flag / unflag\n\n"
            "Left click on an opened number: if it has exactly that many "
            "flags around, opens all other neighbours\n"
            "(a wrong flag means a mine, so be careful)\n\n"
            "Right click on an opened number: if the number of closed "
            "neighbours equals the number, flags all of them\n\n"
            "Middle click on a number: same as the left click, always\n"
            "F2: new game\n\n"
            "Both number features can be turned off in Options.",
            parent=self.window,
        )

    # --------------------------------------------------
    # FIELD
    # --------------------------------------------------

    def _set_field(self, rows, cols, mines):
        self.rows, self.cols, self.mines = rows, cols, mines
        self._save_settings()
        self.new_game()

    def _sync_preset_var(self):
        field = (self.rows, self.cols, self.mines)
        name = next((n for n, f in PRESETS.items() if f == field), "Custom")
        self.preset_var.set(name)

    def _custom_dialog(self):
        dlg = tk.Toplevel(self.window)
        dlg.title("Custom field")
        dlg.resizable(False, False)
        dlg.transient(self.window)

        frame = ttk.Frame(dlg, padding=14)
        frame.pack(fill="both", expand=True)

        rows_var = tk.StringVar(master=dlg, value=str(self.rows))
        cols_var = tk.StringVar(master=dlg, value=str(self.cols))
        mines_var = tk.StringVar(master=dlg, value=str(self.mines))

        for row, (label, var, low, high) in enumerate((
            ("Height (rows)", rows_var, MIN_SIDE, MAX_ROWS),
            ("Width (columns)", cols_var, MIN_SIDE, MAX_COLS),
            ("Mines", mines_var, 1, MAX_ROWS * MAX_COLS),
        )):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Spinbox(
                frame, textvariable=var, from_=low, to=high, width=8,
            ).grid(row=row, column=1, padx=(12, 0))

        hint = ttk.Label(
            frame, foreground="#666666", justify="left",
            text=f"Height {MIN_SIDE}-{MAX_ROWS}, width {MIN_SIDE}-{MAX_COLS}.\n"
                 f"The first click is always safe.",
        )
        hint.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

        error_label = ttk.Label(frame, foreground="#c53030", wraplength=260)
        error_label.grid(row=4, column=0, columnspan=2, sticky="w")

        def cancel():
            dlg.destroy()
            self._sync_preset_var()

        def apply():
            try:
                rows = int(rows_var.get())
                cols = int(cols_var.get())
                mines = int(mines_var.get())
            except ValueError:
                error_label.config(text="Enter whole numbers.")
                return

            error = validate_field(rows, cols, mines)
            if error:
                error_label.config(text=error)
                return

            dlg.destroy()
            self._set_field(rows, cols, mines)

        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Start", command=apply).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Cancel", command=cancel).pack(side="left")

        dlg.protocol("WM_DELETE_WINDOW", cancel)
        dlg.bind("<Return>", lambda e: apply())
        dlg.bind("<Escape>", lambda e: cancel())

        try:
            dlg.wait_visibility()
            dlg.grab_set()
        except tk.TclError:
            pass

    def _build_grid(self):
        for widget in self.board_frame.winfo_children():
            widget.destroy()

        self.cells = {}
        font = ("Arial", 12 if self.cols <= 30 else 10, "bold")

        for r in range(self.rows):
            for c in range(self.cols):
                label = tk.Label(
                    self.board_frame, text="", font=font, width=3, height=1,
                    bg=HIDDEN_BG, relief="raised", bd=2,
                )
                label.grid(row=r, column=c)

                label.bind("<Button-1>", lambda e, r=r, c=c: self._left_click(r, c))
                label.bind(RIGHT_CLICK, lambda e, r=r, c=c: self._right_click(r, c))
                label.bind(MIDDLE_CLICK, lambda e, r=r, c=c: self._middle_click(r, c))

                self.cells[(r, c)] = label

        self.grid_size = (self.rows, self.cols)

    # --------------------------------------------------
    # GAME FLOW
    # --------------------------------------------------

    def new_game(self):
        self._stop_timer()
        self.seconds = 0
        self.timer_label.config(text="000")

        self.board = Board(self.rows, self.cols, self.mines)

        if self.grid_size != (self.rows, self.cols):
            self._build_grid()
        else:
            for cell in self.cells:
                self._paint(*cell)

        self.smiley.config(text="🙂")
        self.status_var.set(
            "Left: open  ·  Right: flag  ·  Click a number: open / flag neighbours"
        )
        self._update_counter()
        self._sync_preset_var()

    def _paint(self, row, col):
        label = self.cells[(row, col)]
        board = self.board
        cell = (row, col)

        if cell in board.revealed:
            number = board.numbers[row][col]
            label.config(
                text=str(number) if number else "",
                fg=NUMBER_COLORS.get(number, "black"),
                bg=OPEN_BG, relief="flat",
            )
        elif cell in board.flags:
            label.config(text="🚩", fg="red", bg=HIDDEN_BG, relief="raised")
        else:
            label.config(text="", fg="black", bg=HIDDEN_BG, relief="raised")

    def _update_counter(self):
        remaining = max(self.board.remaining, -99)
        self.counter_label.config(text=f"{remaining:03d}")

    def _apply(self, changes: Changes):
        for cell in [*changes.revealed, *changes.flagged, *changes.unflagged]:
            self._paint(*cell)

        self._update_counter()

        state = self.board.state

        if state == "playing" and self.timer_job is None:
            self._start_timer()
        elif state == "lost":
            self._on_lost(changes.exploded)
        elif state == "won":
            self._on_won()

    def _on_lost(self, exploded):
        self._stop_timer()
        self.smiley.config(text="😵")

        for row, col in self.board.hidden_mines():
            self.cells[(row, col)].config(text="💣", bg="red", relief="sunken")

        for row, col in self.board.wrong_flags():
            self.cells[(row, col)].config(text="❌", bg="#ffb74d", relief="sunken")

        if exploded:
            self.cells[exploded].config(bg="#8b0000", fg="white")

        self.status_var.set("BOOM! You hit a mine.  Press F2 or the face for a new game.")

    def _on_won(self):
        self._stop_timer()
        self.smiley.config(text="😎")

        for row, col in self.board.mines:
            self.cells[(row, col)].config(text="💣", bg="#7bd88f", relief="sunken")

        self.status_var.set(f"You win!  Time: {self.seconds} s")

    # --------------------------------------------------
    # MOUSE
    # --------------------------------------------------

    def _left_click(self, row, col):
        board = self.board

        if board.state in ("won", "lost"):
            return

        if (row, col) in board.revealed:
            if self.chord_var.get():
                self._apply(board.chord(row, col))
        else:
            self._apply(board.open_cell(row, col))

    def _right_click(self, row, col):
        board = self.board

        if board.state in ("won", "lost"):
            return

        if (row, col) in board.revealed:
            if self.auto_flag_var.get():
                self._apply(board.auto_flag(row, col))
        else:
            self._apply(board.toggle_flag(row, col))

    def _middle_click(self, row, col):
        self._apply(self.board.chord(row, col))

    # --------------------------------------------------
    # TIMER / CLOSE
    # --------------------------------------------------

    def _start_timer(self):
        self.timer_job = self.window.after(1000, self._tick)

    def _tick(self):
        if not self.alive:
            return

        self.seconds += 1
        self.timer_label.config(text=f"{min(self.seconds, 999):03d}")
        self.timer_job = self.window.after(1000, self._tick)

    def _stop_timer(self):
        if self.timer_job is not None:
            try:
                self.window.after_cancel(self.timer_job)
            except tk.TclError:
                pass
            self.timer_job = None

    def close(self):
        if not self.alive:
            return

        self.alive = False
        self._stop_timer()
        self._save_settings()

        try:
            self.window.destroy()
        except tk.TclError:
            pass


# ============================================================
# ENTRY POINT
# ============================================================

def _storage_path(base_dir):
    if base_dir:
        return Path(base_dir) / "db" / "minesweeper.json"
    return Path(__file__).resolve().with_name("minesweeper_settings.json")


def main(parent=None, base_dir=None):
    """
    main()                       separate window, as before
    main(ctx.root, ctx.base_dir) a window inside Toolkit (no second Tk root,
                                 no nested mainloop); settings go to db/
    """
    if parent is None:
        root = tk.Tk()
        game = Minesweeper(root, _storage_path(base_dir))
        root.mainloop()
        return game

    window = tk.Toplevel(parent)
    return Minesweeper(window, _storage_path(base_dir))


if __name__ == "__main__":
    main()