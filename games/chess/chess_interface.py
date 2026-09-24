from pathlib import Path
import tkinter as tk
from tkinter import ttk

from .chess_driver import Chess


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
    def __init__(self, root):
        self.root = root

        self.root.title("Chess")
        self.root.resizable(False, False)

        self.game = Chess()

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

        for color in ("White", "Black"):
            for piece_name in (
                "Pawn",
                "Knight",
                "Bishop",
                "Rook",
                "Queen",
                "King",
            ):
                filename = (
                    f"Piece={piece_name}, "
                    f"Side={color}.png"
                )

                path = assets_dir / filename

                if path.exists():
                    key = (
                        ("w" if color == "White" else "b")
                        + {
                            "Pawn": "p",
                            "Knight": "n",
                            "Bishop": "b",
                            "Rook": "r",
                            "Queen": "q",
                            "King": "k",
                        }[piece_name]
                    )

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

        # -----------------------------------------------------
        # Board
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Sidebar
        # -----------------------------------------------------

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

        # Title
        tk.Label(
            panel,
            text="CHESS",
            font=("Arial", 18, "bold"),
        ).pack(
            pady=(0, 10),
        )

        # Turn
        self.turn_label = tk.Label(
            panel,
            text="",
            font=("Arial", 11, "bold"),
        )

        self.turn_label.pack(
            pady=(0, 5),
        )

        # Status
        self.status_label = tk.Label(
            panel,
            text="",
            wraplength=190,
            justify="center",
        )

        self.status_label.pack(
            pady=(0, 10),
        )

        # Captured
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

        # Move history
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

        # New Game
        tk.Button(
            panel,
            text="New Game",
            command=self.new_game,
        ).pack(
            fill="x",
            pady=(0, 5),
        )

        # Close
        tk.Button(
            panel,
            text="Close",
            command=self.root.destroy,
        ).pack(
            fill="x",
        )

    # =========================================================
    # BOARD RENDERING
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

        # -----------------------------------------------------
        # Last move
        # -----------------------------------------------------

        if self.game.last_move is not None:
            move = self.game.last_move

            if (
                (row, col) == move["from"]
                or (row, col) == move["to"]
            ):
                color = LAST_MOVE_COLOR

        # -----------------------------------------------------
        # King in check
        # -----------------------------------------------------

        piece = self.game.board[row][col]

        if piece is not None and piece[1] == "k":
            if self.game.is_in_check(piece[0]):
                color = CHECK_COLOR

        # -----------------------------------------------------
        # Possible moves
        # -----------------------------------------------------

        if (row, col) in self.possible_moves:
            if piece is None:
                color = MOVE_COLOR
            else:
                color = CAPTURE_COLOR

        # -----------------------------------------------------
        # Selected square
        # -----------------------------------------------------

        if self.selected == (row, col):
            color = SELECTED_COLOR

        # -----------------------------------------------------
        # Piece image
        # -----------------------------------------------------

        if piece is not None:
            image = self.images.get(piece)

            button.config(
                bg=color,
                activebackground=color,
                image=image,
            )

            button.image = image

        else:
            button.config(
                bg=color,
                activebackground=color,
                image="",
            )

            button.image = None

    # =========================================================
    # CLICK HANDLING
    # =========================================================

    def square_click(self, row, col):
        if self.game.game_over:
            return

        piece = self.game.board[row][col]

        # -----------------------------------------------------
        # Nothing selected
        # -----------------------------------------------------

        if self.selected is None:
            if piece is None:
                return

            if piece[0] != self.game.turn:
                return

            self.select_piece(row, col)

            return

        # -----------------------------------------------------
        # Selecting another own piece
        # -----------------------------------------------------

        if piece is not None:
            if piece[0] == self.game.turn:
                self.select_piece(row, col)

                return

        # -----------------------------------------------------
        # Move
        # -----------------------------------------------------

        if (row, col) in self.possible_moves:
            self.try_move(row, col)

            return

        # -----------------------------------------------------
        # Invalid square
        # -----------------------------------------------------

        self.clear_selection()

    def select_piece(self, row, col):
        self.selected = (row, col)

        self.possible_moves = self.game.get_legal_moves(
            row,
            col,
        )

        self.render_board()

    def clear_selection(self):
        self.selected = None
        self.possible_moves = []

        self.render_board()

    # =========================================================
    # MOVE
    # =========================================================

    def try_move(self, row, col):
        if self.selected is None:
            return

        from_row, from_col = self.selected

        piece = self.game.board[from_row][from_col]

        promotion_piece = None

        # -----------------------------------------------------
        # Promotion
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Execute move
        # -----------------------------------------------------

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

        self.update_interface()

        result = self.game.check_game_state()

        self.update_interface()

        if result is not None:
            self.show_game_over(result)

    # =========================================================
    # PROMOTION
    # =========================================================

    def ask_promotion(self, color):
        result = {
            "piece": None,
        }

        window = tk.Toplevel(self.root)

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

        pieces = [
            ("q", "Queen"),
            ("r", "Rook"),
            ("b", "Bishop"),
            ("n", "Knight"),
        ]

        for piece_code, name in pieces:
            full_piece = color + piece_code

            image = self.images.get(full_piece)

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

        def choose(piece_code):
            result["piece"] = piece_code

            window.destroy()

        window.wait_window()

        return result["piece"]

    # =========================================================
    # SIDEBAR UPDATE
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
        else:
            self.status_label.config(
                text="Your move"
            )

    def update_captured(self):
        white_captured = self.game.captured_pieces["b"]
        black_captured = self.game.captured_pieces["w"]

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

        for index in range(0, len(moves), 2):
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

        self.history_listbox.yview_moveto(1.0)

    # =========================================================
    # GAME OVER
    # =========================================================

    def show_game_over(self, result):
        window = tk.Toplevel(self.root)

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

        button_frame = tk.Frame(window)

        button_frame.pack(
            padx=20,
            pady=(0, 20),
        )

        tk.Button(
            button_frame,
            text="New Game",
            width=12,
            command=lambda: self.restart_from_window(
                window
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

    def restart_from_window(self, window):
        window.destroy()

        self.new_game()

    # =========================================================
    # NEW GAME
    # =========================================================

    def new_game(self):
        self.game.reset()

        self.selected = None
        self.possible_moves = []

        self.history_listbox.delete(
            0,
            tk.END,
        )

        self.update_interface()


# =============================================================
# ENTRY POINT
# =============================================================

def main():
    root = tk.Toplevel()

    ChessInterface(root)

    root.mainloop()