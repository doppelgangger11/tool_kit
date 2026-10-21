from pathlib import Path

import tkinter as tk
from tkinter import ttk

from .checkers_driver import Checkers
from .bot import CheckersBot


BOARD_SIZE = 8
SQUARE_SIZE = 55

LIGHT_COLOR = "#d6d2c4"
DARK_COLOR = "#8f8b80"

SELECTED_COLOR = "#6f8065"
MOVE_COLOR = "#a0aa91"
CAPTURE_COLOR = "#9b6969"
LAST_MOVE_COLOR = "#b0a878"
MUST_CAPTURE_COLOR = "#c0504d"

WHITE_PIECE = "#f2efe6"
WHITE_OUTLINE = "#5a5750"
BLACK_PIECE = "#3a3733"
BLACK_OUTLINE = "#1d1b19"
KING_MARK = "#c9a227"

PANEL_WIDTH = 220


class CheckersInterface:
    def __init__(
        self,
        root,
        game_mode="Player vs Bot",
        difficulty="Medium",
        bot_color="b",
    ):
        self.root = root

        self.root.title("Checkers")
        self.root.resizable(False, False)

        self.game = Checkers()

        self.game_mode = game_mode
        self.difficulty = difficulty
        self.bot_color = bot_color

        self.bot = None

        if self.game_mode == "Player vs Bot":
            self.bot = CheckersBot(
                color=self.bot_color,
                difficulty=self.difficulty,
            )

        # Selection state.
        #
        # path        - squares already chosen for the current move
        #               (start square + landing squares so far)
        # candidates  - legal moves that start with `path`
        self.path = []
        self.candidates = []

        self.images = {}

        self.load_images()
        self.create_interface()

        self.render_board()
        self.update_interface()

        # Ctrl + Z
        self.root.bind(
            "<Control-z>",
            self.handle_undo,
        )

        # Esc - cancel selection
        self.root.bind(
            "<Escape>",
            lambda event: self.clear_selection(),
        )

    # =========================================================
    # ASSETS
    # =========================================================

    def load_images(self):
        """
        Loads the piece images made by generate_assets.py.

        If the files are missing, the pieces are drawn with canvas shapes,
        so the game works without them.
        """
        assets_dir = Path(__file__).parent / "assets"

        piece_map = {
            "p": "Man",
            "k": "King",
        }

        for color_code, color in (("w", "White"), ("b", "Black")):
            for piece_code, piece_name in piece_map.items():
                path = assets_dir / (
                    f"Piece={piece_name}, "
                    f"Side={color}.png"
                )

                if not path.exists():
                    continue

                try:
                    self.images[color_code + piece_code] = tk.PhotoImage(
                        file=str(path)
                    )
                except tk.TclError:
                    # broken file: fall back to the drawn piece
                    continue

    # =========================================================
    # INTERFACE
    # =========================================================

    def create_interface(self):
        main_frame = tk.Frame(
            self.root,
            bg="#222222",
        )

        main_frame.pack(
            padx=10,
            pady=10,
        )

        self.canvas = tk.Canvas(
            main_frame,
            width=BOARD_SIZE * SQUARE_SIZE,
            height=BOARD_SIZE * SQUARE_SIZE,
            highlightthickness=0,
            bd=0,
        )

        self.canvas.pack(
            side="left",
        )

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-3>", lambda event: self.clear_selection())

        self.create_side_panel(main_frame)

    def create_side_panel(self, parent):
        panel = tk.Frame(
            parent,
            width=PANEL_WIDTH,
            height=BOARD_SIZE * SQUARE_SIZE,
            padx=12,
            pady=10,
        )

        panel.pack(
            side="left",
            fill="y",
            padx=(10, 0),
        )

        panel.pack_propagate(False)

        tk.Label(
            panel,
            text="CHECKERS",
            font=("Arial", 18, "bold"),
        ).pack(
            pady=(0, 5),
        )

        self.mode_label = tk.Label(
            panel,
            text=self.get_mode_text(),
            font=("Arial", 9),
        )

        self.mode_label.pack(
            pady=(0, 5),
        )

        self.turn_label = tk.Label(
            panel,
            text="",
            font=("Arial", 11, "bold"),
        )

        self.turn_label.pack(
            pady=(0, 5),
        )

        self.status_label = tk.Label(
            panel,
            text="",
            wraplength=190,
            justify="center",
        )

        self.status_label.pack(
            pady=(0, 10),
        )

        tk.Label(
            panel,
            text="Captured",
            font=("Arial", 10, "bold"),
        ).pack(
            anchor="w",
        )

        self.captured_label = tk.Label(
            panel,
            text="",
            anchor="w",
            justify="left",
        )

        self.captured_label.pack(
            fill="x",
            pady=(0, 10),
        )

        tk.Label(
            panel,
            text="Moves",
            font=("Arial", 10, "bold"),
        ).pack(
            anchor="w",
        )

        history_frame = tk.Frame(panel)

        history_frame.pack(
            fill="both",
            expand=True,
            pady=(2, 10),
        )

        scrollbar = ttk.Scrollbar(
            history_frame,
            orient="vertical",
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        self.history_listbox = tk.Listbox(
            history_frame,
            height=10,
            yscrollcommand=scrollbar.set,
            activestyle="none",
        )

        self.history_listbox.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.config(
            command=self.history_listbox.yview
        )

        # -----------------------------------------------------
        # Undo
        # -----------------------------------------------------

        self.undo_button = tk.Button(
            panel,
            text="Undo",
            command=self.undo_move,
        )

        self.undo_button.pack(
            fill="x",
            pady=(0, 5),
        )

        # -----------------------------------------------------
        # New Game
        # -----------------------------------------------------

        tk.Button(
            panel,
            text="New Game",
            command=self.new_game_dialog,
        ).pack(
            fill="x",
            pady=(0, 5),
        )

        tk.Button(
            panel,
            text="Close",
            command=self.root.destroy,
        ).pack(
            fill="x",
        )

    def get_mode_text(self):
        if self.game_mode == "Player vs Bot":
            return f"Bot: {self.difficulty}"

        return "Player vs Player"

    # =========================================================
    # UNDO
    # =========================================================

    def handle_undo(self, event=None):
        self.undo_move()

    def undo_move(self):
        # Nothing to undo
        if not self.game.state_history:
            return

        # Do not allow undo while bot is making its move
        if self.is_bot_turn():
            return

        # PvP: undo one move
        if self.game_mode == "Player vs Player":
            self.game.undo()

        # PvBot: undo bot's move + player's move
        else:
            self.game.undo()

            if (
                self.game.turn == self.bot_color
                and self.game.state_history
            ):
                self.game.undo()

        self.path = []
        self.candidates = []

        self.update_interface()

    # =========================================================
    # BOARD
    # =========================================================

    @staticmethod
    def is_dark_square(row, col):
        return (row + col) % 2 == 1

    def get_square_color(self, row, col):
        if self.is_dark_square(row, col):
            return DARK_COLOR

        return LIGHT_COLOR

    def next_squares(self):
        """
        Squares the player can click next for the move in progress.
        """
        step = len(self.path)

        return {
            move["path"][step]
            for move in self.candidates
            if len(move["path"]) > step
        }

    def render_board(self):
        canvas = self.canvas

        canvas.delete("all")

        last_squares = set()

        if self.game.last_move is not None:
            last_squares = set(self.game.last_move["path"])

        targets = self.next_squares()

        # Squares where a capture is mandatory (shown when nothing is selected).
        must_capture = set()

        if not self.path and not self.game.game_over:
            if not self.is_bot_turn():
                must_capture = self.game.pieces_that_must_capture()

        # Squares that will be captured by the move in progress.
        capturing = set()

        if self.path:
            for move in self.candidates:
                capturing.update(move["captures"])

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                x1 = col * SQUARE_SIZE
                y1 = row * SQUARE_SIZE
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE

                color = self.get_square_color(row, col)

                if (row, col) in last_squares:
                    color = LAST_MOVE_COLOR

                if (row, col) in self.path:
                    color = SELECTED_COLOR

                if (row, col) in targets:
                    color = MOVE_COLOR

                canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=color,
                    outline="",
                )

                piece = self.game.board[row][col]

                if piece is not None:
                    if (row, col) in capturing and (row, col) not in self.path:
                        canvas.create_rectangle(
                            x1 + 2, y1 + 2, x2 - 2, y2 - 2,
                            outline=CAPTURE_COLOR,
                            width=2,
                        )

                    self.draw_piece(
                        piece,
                        x1,
                        y1,
                        highlight=(row, col) in must_capture,
                    )

                elif (row, col) in targets:
                    cx = x1 + SQUARE_SIZE // 2
                    cy = y1 + SQUARE_SIZE // 2

                    canvas.create_oval(
                        cx - 6, cy - 6, cx + 6, cy + 6,
                        fill=SELECTED_COLOR,
                        outline="",
                    )

    def draw_piece(self, piece, x, y, highlight=False):
        image = self.images.get(piece)

        if image is None:
            self.draw_vector_piece(piece, x, y, highlight)
            return

        if highlight:
            # red ring around a piece that has to capture
            self.canvas.create_oval(
                x + 3,
                y + 3,
                x + SQUARE_SIZE - 3,
                y + SQUARE_SIZE - 3,
                outline=MUST_CAPTURE_COLOR,
                width=3,
            )

        self.canvas.create_image(
            x + SQUARE_SIZE // 2,
            y + SQUARE_SIZE // 2,
            image=image,
        )

    def draw_vector_piece(self, piece, x, y, highlight=False):
        margin = 7

        if piece[0] == "w":
            fill = WHITE_PIECE
            outline = WHITE_OUTLINE
        else:
            fill = BLACK_PIECE
            outline = BLACK_OUTLINE

        if highlight:
            outline = MUST_CAPTURE_COLOR

        self.canvas.create_oval(
            x + margin,
            y + margin,
            x + SQUARE_SIZE - margin,
            y + SQUARE_SIZE - margin,
            fill=fill,
            outline=outline,
            width=3 if highlight else 2,
        )

        # inner ring makes the pieces look like real draughts
        inner = margin + 7

        self.canvas.create_oval(
            x + inner,
            y + inner,
            x + SQUARE_SIZE - inner,
            y + SQUARE_SIZE - inner,
            fill="",
            outline=outline,
            width=1,
        )

        if piece[1] == "k":
            self.canvas.create_text(
                x + SQUARE_SIZE // 2,
                y + SQUARE_SIZE // 2,
                text=self.game.get_piece_symbol(piece),
                fill=KING_MARK,
                font=("Arial", 18, "bold"),
            )

    # =========================================================
    # CLICK
    # =========================================================

    def on_click(self, event):
        col = event.x // SQUARE_SIZE
        row = event.y // SQUARE_SIZE

        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            return

        self.square_click(row, col)

    def square_click(self, row, col):
        if self.game.game_over:
            return

        if self.is_bot_turn():
            return

        piece = self.game.board[row][col]

        # A move is in progress.
        if self.path:
            if (row, col) in self.next_squares():
                self.advance_path(row, col)
                return

            # Only just selected (no jump made yet): allow re-selecting
            # another piece or cancelling.
            if len(self.path) == 1:
                if piece is not None and piece[0] == self.game.turn:
                    self.select_piece(row, col)
                else:
                    self.clear_selection()

            # In the middle of a multi-jump the move has to be finished.
            return

        if piece is None or piece[0] != self.game.turn:
            return

        self.select_piece(row, col)

    def select_piece(self, row, col):
        moves = self.game.get_legal_moves(row, col)

        if not moves:
            self.path = []
            self.candidates = []

            if self.game.has_forced_capture():
                self.status_label.config(
                    text="Capture is mandatory"
                )

            self.render_board()
            return

        self.path = [(row, col)]
        self.candidates = moves

        self.render_board()

    def clear_selection(self):
        # A multi-jump in progress cannot be cancelled.
        if len(self.path) > 1:
            return

        self.path = []
        self.candidates = []

        self.render_board()

    # =========================================================
    # PLAYER MOVE
    # =========================================================

    def advance_path(self, row, col):
        new_path = self.path + [(row, col)]

        self.candidates = [
            move
            for move in self.candidates
            if move["path"][:len(new_path)] == new_path
        ]

        self.path = new_path

        finished = [
            move
            for move in self.candidates
            if len(move["path"]) == len(new_path)
        ]

        if not finished:
            # The capture continues: wait for the next landing square.
            self.render_board()
            return

        move = finished[0]

        if not self.game.make_move(move):
            self.path = []
            self.candidates = []
            self.render_board()
            return

        self.path = []
        self.candidates = []

        self.finish_turn()

    # =========================================================
    # TURN FINISH
    # =========================================================

    def finish_turn(self):
        self.update_interface()

        result = self.game.check_game_state()

        self.update_interface()

        if result is not None:
            self.show_game_over(result)
            return

        if self.is_bot_turn():
            self.root.after(
                250,
                self.make_bot_move,
            )

    # =========================================================
    # BOT
    # =========================================================

    def is_bot_turn(self):
        if self.game_mode != "Player vs Bot":
            return False

        return self.game.turn == self.bot_color

    def make_bot_move(self):
        if self.game.game_over:
            return

        if not self.is_bot_turn():
            return

        self.status_label.config(
            text="Bot is thinking..."
        )

        self.root.update_idletasks()

        move = self.bot.make_move(
            self.game
        )

        if move is None:
            return

        if not self.game.make_move(move):
            return

        self.path = []
        self.candidates = []

        self.finish_turn()

    # =========================================================
    # UPDATE
    # =========================================================

    def update_interface(self):
        self.update_turn()
        self.update_status()
        self.update_captured()
        self.update_history()
        self.update_undo_button()
        self.render_board()

    def update_turn(self):
        if self.game.turn == "w":
            text = "Turn: White"
        else:
            text = "Turn: Black"

        self.turn_label.config(
            text=text,
        )

    def update_status(self):
        if self.game.game_over:
            return

        if self.is_bot_turn():
            self.status_label.config(
                text="Bot is thinking..."
            )
        elif self.game.has_forced_capture():
            self.status_label.config(
                text="Capture is mandatory"
            )
        else:
            self.status_label.config(
                text="Your move"
            )

    def update_undo_button(self):
        if not self.game.state_history:
            self.undo_button.config(
                state="disabled"
            )

        elif self.is_bot_turn():
            self.undo_button.config(
                state="disabled"
            )

        else:
            self.undo_button.config(
                state="normal"
            )

    def update_captured(self):
        white_captured = (
            self.game.captured_pieces["b"]
        )

        black_captured = (
            self.game.captured_pieces["w"]
        )

        white_text = "".join(
            self.game.get_piece_symbol(piece)
            for piece in white_captured
        )

        black_text = "".join(
            self.game.get_piece_symbol(piece)
            for piece in black_captured
        )

        text = (
            f"White: {white_text}\n"
            f"Black: {black_text}"
        )

        self.captured_label.config(
            text=text,
        )

    def update_history(self):
        self.history_listbox.delete(
            0,
            tk.END,
        )

        moves = self.game.move_history

        for index in range(
            0,
            len(moves),
            2,
        ):
            white_move = moves[index]

            if index + 1 < len(moves):
                black_move = moves[index + 1]

                text = (
                    f"{index // 2 + 1}. "
                    f"{white_move:<12}"
                    f"{black_move}"
                )
            else:
                text = (
                    f"{index // 2 + 1}. "
                    f"{white_move}"
                )

            self.history_listbox.insert(
                tk.END,
                text,
            )

        self.history_listbox.yview_moveto(
            1.0
        )

    # =========================================================
    # GAME OVER
    # =========================================================

    def get_result_text(self, result):
        if result["type"] == "win":
            winner = "White" if result["winner"] == "w" else "Black"
            loser = "Black" if result["winner"] == "w" else "White"

            if result["reason"] == "no_pieces":
                return f"{winner} wins!\n{loser} has no pieces left."

            return f"{winner} wins!\n{loser} cannot move."

        if result["reason"] == "repetition":
            return "Draw.\nThe position repeated three times."

        return "Draw.\nFifteen moves by kings without a capture."

    def show_game_over(self, result):
        window = tk.Toplevel(
            self.root
        )

        window.title("Game Over")
        window.resizable(False, False)

        window.transient(self.root)
        window.grab_set()

        tk.Label(
            window,
            text=self.get_result_text(result),
            font=("Arial", 14, "bold"),
            justify="center",
        ).pack(
            padx=30,
            pady=(25, 20),
        )

        button_frame = tk.Frame(
            window
        )

        button_frame.pack(
            padx=20,
            pady=(0, 20),
        )

        tk.Button(
            button_frame,
            text="New Game",
            width=12,
            command=lambda: (
                window.destroy(),
                self.new_game_dialog(),
            ),
        ).pack(
            side="left",
            padx=5,
        )

        tk.Button(
            button_frame,
            text="Close",
            width=12,
            command=self.root.destroy,
        ).pack(
            side="left",
            padx=5,
        )

    # =========================================================
    # NEW GAME
    # =========================================================

    def new_game_dialog(self):
        self.show_setup_window()

    # =========================================================
    # SETUP
    # =========================================================

    def show_setup_window(self):
        window = tk.Toplevel(
            self.root
        )

        window.title("New Checkers Game")
        window.resizable(False, False)

        window.transient(self.root)
        window.grab_set()

        frame = tk.Frame(
            window,
            padx=20,
            pady=20,
        )

        frame.pack()

        tk.Label(
            frame,
            text="New Checkers Game",
            font=("Arial", 15, "bold"),
        ).pack(
            pady=(0, 15),
        )

        # -----------------------------------------------------
        # Game mode
        # -----------------------------------------------------

        tk.Label(
            frame,
            text="Game mode:",
            font=("Arial", 10, "bold"),
        ).pack(
            anchor="w",
        )

        mode_var = tk.StringVar(
            value=self.game_mode
        )

        tk.Radiobutton(
            frame,
            text="Player vs Bot",
            variable=mode_var,
            value="Player vs Bot",
        ).pack(
            anchor="w",
        )

        tk.Radiobutton(
            frame,
            text="Player vs Player",
            variable=mode_var,
            value="Player vs Player",
        ).pack(
            anchor="w",
        )

        # -----------------------------------------------------
        # Difficulty
        # -----------------------------------------------------

        tk.Label(
            frame,
            text="Difficulty:",
            font=("Arial", 10, "bold"),
        ).pack(
            anchor="w",
            pady=(15, 3),
        )

        difficulty_var = tk.StringVar(
            value=self.difficulty
        )

        difficulty_box = ttk.Combobox(
            frame,
            textvariable=difficulty_var,
            values=[
                "Easy",
                "Medium",
                "Hard",
                "Expert",
            ],
            state="readonly",
            width=18,
        )

        difficulty_box.pack(
            anchor="w",
        )

        # -----------------------------------------------------
        # Buttons
        # -----------------------------------------------------

        button_frame = tk.Frame(
            frame
        )

        button_frame.pack(
            pady=(20, 0),
        )

        def start_game():
            self.game_mode = mode_var.get()
            self.difficulty = (
                difficulty_var.get()
            )

            if self.game_mode == "Player vs Bot":
                self.bot = CheckersBot(
                    color=self.bot_color,
                    difficulty=self.difficulty,
                )
            else:
                self.bot = None

            self.game.reset()

            self.path = []
            self.candidates = []

            window.destroy()

            self.mode_label.config(
                text=self.get_mode_text()
            )

            self.update_interface()

            if self.is_bot_turn():
                self.root.after(
                    250,
                    self.make_bot_move,
                )

        tk.Button(
            button_frame,
            text="Start",
            width=12,
            command=start_game,
        ).pack(
            side="left",
            padx=5,
        )

        tk.Button(
            button_frame,
            text="Cancel",
            width=12,
            command=window.destroy,
        ).pack(
            side="left",
            padx=5,
        )

    # =========================================================
    # STARTUP
    # =========================================================

    def show_initial_setup(self):
        self.show_setup_window()


def main():
    root = tk.Toplevel()

    root.withdraw()

    interface = CheckersInterface(
        root,
        game_mode="Player vs Bot",
        difficulty="Medium",
        bot_color="b",
    )

    root.deiconify()

    interface.show_initial_setup()
