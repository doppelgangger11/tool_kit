from pathlib import Path
import tkinter as tk
from tkinter import ttk

from .chess_driver import Chess
from .bot import ChessBot


BOARD_SIZE = 8
SQUARE_SIZE = 55

LIGHT_COLOR = "#d6d2c4"
DARK_COLOR = "#8f8b80"

SELECTED_COLOR = "#6f8065"
MOVE_COLOR = "#a0aa91"
CAPTURE_COLOR = "#9b6969"
LAST_MOVE_COLOR = "#b0a878"
CHECK_COLOR = "#9b5c5c"

PANEL_WIDTH = 220


class ChessInterface:
    def __init__(
        self,
        root,
        game_mode="Player vs Bot",
        difficulty="Medium",
        bot_color="b",
    ):
        self.root = root

        self.root.title("Chess")
        self.root.resizable(False, False)

        self.game = Chess()

        self.game_mode = game_mode
        self.difficulty = difficulty
        self.bot_color = bot_color

        self.bot = None

        if self.game_mode == "Player vs Bot":
            self.bot = ChessBot(
                color=self.bot_color,
                difficulty=self.difficulty,
            )

        self.selected = None
        self.possible_moves = []

        self.buttons = []
        self.images = {}

        self.load_images()
        self.create_interface()

        self.render_board()
        self.update_interface()

    # =========================================================
    # ASSETS
    # =========================================================

    def load_images(self):
        assets_dir = Path(__file__).parent / "assets"

        piece_map = {
            "Pawn": "p",
            "Knight": "n",
            "Bishop": "b",
            "Rook": "r",
            "Queen": "q",
            "King": "k",
        }

        for color in ("White", "Black"):
            color_code = (
                "w"
                if color == "White"
                else "b"
            )

            for piece_name, piece_code in piece_map.items():
                filename = (
                    f"Piece={piece_name}, "
                    f"Side={color}.png"
                )

                path = assets_dir / filename

                if path.exists():
                    key = color_code + piece_code

                    self.images[key] = tk.PhotoImage(
                        file=str(path)
                    )

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

        board_frame = tk.Frame(
            main_frame,
            width=BOARD_SIZE * SQUARE_SIZE,
            height=BOARD_SIZE * SQUARE_SIZE,
        )

        board_frame.pack(
            side="left",
        )

        board_frame.pack_propagate(False)

        self.board_frame = board_frame

        for row in range(BOARD_SIZE):
            row_buttons = []

            for col in range(BOARD_SIZE):
                button = tk.Button(
                    board_frame,
                    relief="flat",
                    bd=0,
                    highlightthickness=0,
                    padx=0,
                    pady=0,
                    command=lambda r=row, c=col: (
                        self.square_click(r, c)
                    ),
                )

                button.place(
                    x=col * SQUARE_SIZE,
                    y=row * SQUARE_SIZE,
                    width=SQUARE_SIZE,
                    height=SQUARE_SIZE,
                )

                row_buttons.append(button)

            self.buttons.append(row_buttons)

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
            text="CHESS",
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
    # BOARD
    # =========================================================

    def get_square_color(self, row, col):
        if (row + col) % 2 == 0:
            return LIGHT_COLOR

        return DARK_COLOR

    def render_board(self):
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                self.render_square(row, col)

    def render_square(self, row, col):
        button = self.buttons[row][col]

        color = self.get_square_color(
            row,
            col,
        )

        if self.game.last_move is not None:
            move = self.game.last_move

            if (
                (row, col) == move["from"]
                or (row, col) == move["to"]
            ):
                color = LAST_MOVE_COLOR

        piece = self.game.board[row][col]

        if piece is not None and piece[1] == "k":
            if self.game.is_in_check(piece[0]):
                color = CHECK_COLOR

        if (row, col) in self.possible_moves:
            if piece is None:
                color = MOVE_COLOR
            else:
                color = CAPTURE_COLOR

        if self.selected == (row, col):
            color = SELECTED_COLOR

        # Always clear old image first.
        button.config(
            bg=color,
            activebackground=color,
            image="",
        )

        button.image = None

        if piece is not None:
            image = self.images.get(piece)

            button.config(
                image=image,
            )

            button.image = image

    # =========================================================
    # CLICK
    # =========================================================

    def square_click(self, row, col):
        if self.game.game_over:
            return

        if self.is_bot_turn():
            return

        piece = self.game.board[row][col]

        if self.selected is None:
            if piece is None:
                return

            if piece[0] != self.game.turn:
                return

            self.select_piece(
                row,
                col,
            )

            return

        if piece is not None:
            if piece[0] == self.game.turn:
                self.select_piece(
                    row,
                    col,
                )

                return

        if (row, col) in self.possible_moves:
            self.try_move(
                row,
                col,
            )

            return

        self.clear_selection()

    def select_piece(self, row, col):
        self.selected = (
            row,
            col,
        )

        self.possible_moves = (
            self.game.get_legal_moves(
                row,
                col,
            )
        )

        self.render_board()

    def clear_selection(self):
        self.selected = None
        self.possible_moves = []

        self.render_board()

    # =========================================================
    # PLAYER MOVE
    # =========================================================

    def try_move(self, row, col):
        if self.selected is None:
            return

        from_row, from_col = self.selected

        piece = self.game.board[
            from_row
        ][from_col]

        promotion_piece = None

        if (
            piece is not None
            and piece[1] == "p"
            and row in (0, 7)
        ):
            promotion_piece = self.ask_promotion(
                piece[0]
            )

            if promotion_piece is None:
                return

        success = self.game.move_piece(
            from_row,
            from_col,
            row,
            col,
            promotion_piece=promotion_piece,
        )

        if not success:
            return

        self.selected = None
        self.possible_moves = []

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

        (
            from_row,
            from_col,
            to_row,
            to_col,
            promotion,
        ) = move

        success = self.game.move_piece(
            from_row,
            from_col,
            to_row,
            to_col,
            promotion_piece=promotion,
        )

        if not success:
            return

        self.selected = None
        self.possible_moves = []

        self.finish_turn()

    # =========================================================
    # PROMOTION
    # =========================================================

    def ask_promotion(self, color):
        result = {
            "piece": None,
        }

        window = tk.Toplevel(
            self.root
        )

        window.title("Promotion")
        window.resizable(False, False)

        window.transient(self.root)
        window.grab_set()

        tk.Label(
            window,
            text="Choose promotion:",
            font=("Arial", 11, "bold"),
        ).pack(
            padx=15,
            pady=(15, 10),
        )

        frame = tk.Frame(window)

        frame.pack(
            padx=10,
            pady=(0, 15),
        )

        def choose(piece_code):
            result["piece"] = piece_code
            window.destroy()

        pieces = [
            ("q", "Queen"),
            ("r", "Rook"),
            ("b", "Bishop"),
            ("n", "Knight"),
        ]

        for piece_code, name in pieces:
            full_piece = (
                color + piece_code
            )

            image = self.images.get(
                full_piece
            )

            button = tk.Button(
                frame,
                text=name,
                image=image,
                compound="top",
                command=lambda p=piece_code: (
                    choose(p)
                ),
            )

            button.image = image

            button.pack(
                side="left",
                padx=3,
            )

        window.wait_window()

        return result["piece"]

    # =========================================================
    # INTERFACE UPDATE
    # =========================================================

    def update_interface(self):
        self.update_turn()
        self.update_status()
        self.update_captured()
        self.update_history()
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

        color = self.game.turn

        if self.game.is_in_check(color):
            self.status_label.config(
                text="Check!"
            )
        elif self.is_bot_turn():
            self.status_label.config(
                text="Bot is thinking..."
            )
        else:
            self.status_label.config(
                text="Your move"
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
                    f"{white_move:<8}"
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

    def show_game_over(self, result):
        window = tk.Toplevel(
            self.root
        )

        window.title("Game Over")
        window.resizable(False, False)

        window.transient(self.root)
        window.grab_set()

        if result["type"] == "checkmate":
            winner = result["winner"]

            if winner == "w":
                text = "Checkmate!\nWhite wins!"
            else:
                text = "Checkmate!\nBlack wins!"

        else:
            text = "Stalemate!\nDraw."

        tk.Label(
            window,
            text=text,
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

        window.title("New Chess Game")
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
            text="New Chess Game",
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
                self.bot = ChessBot(
                    color=self.bot_color,
                    difficulty=self.difficulty,
                )
            else:
                self.bot = None

            self.game.reset()

            self.selected = None
            self.possible_moves = []

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

    interface = ChessInterface(
        root,
        game_mode="Player vs Bot",
        difficulty="Medium",
        bot_color="b",
    )

    root.deiconify()

    interface.show_initial_setup()

    root.mainloop()