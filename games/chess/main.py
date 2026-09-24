import tkinter as tk
from pathlib import Path


class Chess:
    BOARD_SIZE = 8
    SQUARE_SIZE = 55

    LIGHT_COLOR = "#d6d2c4"
    DARK_COLOR = "#8f8b80"
    SELECTED_COLOR = "#6f8065"

    def __init__(self, root):
        self.root = root
        self.root.title("Chess")
        self.root.resizable(False, False)

        self.base_dir = Path(__file__).resolve().parent
        self.assets_dir = self.base_dir / "assets"

        self.turn = "w"
        self.selected = None
        self.possible_moves = []

        self.images = {}
        self.squares = []

        self.board = [
            ["br", "bn", "bb", "bq", "bk", "bb", "bn", "br"],
            ["bp", "bp", "bp", "bp", "bp", "bp", "bp", "bp"],
            [None, None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None],
            ["wp", "wp", "wp", "wp", "wp", "wp", "wp", "wp"],
            ["wr", "wn", "wb", "wq", "wk", "wb", "wn", "wr"],
        ]

        self.load_images()
        self.create_board()

    # ==========================================================
    # ASSETS
    # ==========================================================

    def load_images(self):
        pieces = {
            "k": "King",
            "q": "Queen",
            "r": "Rook",
            "b": "Bishop",
            "n": "Knight",
            "p": "Pawn",
        }

        for side_code, side_name in [
            ("w", "White"),
            ("b", "Black"),
        ]:
            for piece_code, piece_name in pieces.items():
                filename = (
                    f"Piece={piece_name}, Side={side_name}.png"
                )

                path = self.assets_dir / filename

                if not path.exists():
                    raise FileNotFoundError(
                        f"Не найден asset:\n{path}"
                    )

                image = tk.PhotoImage(file=path)

                self.images[f"{side_code}{piece_code}"] = image

    # ==========================================================
    # BOARD
    # ==========================================================

    def create_board(self):
        for row in range(self.BOARD_SIZE):
            row_squares = []

            for col in range(self.BOARD_SIZE):
                square_color = self.get_square_color(row, col)

                frame = tk.Frame(
                    self.root,
                    width=self.SQUARE_SIZE,
                    height=self.SQUARE_SIZE,
                    bg=square_color,
                    highlightthickness=0,
                )

                frame.grid(
                    row=row,
                    column=col,
                    padx=0,
                    pady=0,
                )

                frame.grid_propagate(False)

                button = tk.Button(
                    frame,
                    relief="flat",
                    borderwidth=0,
                    highlightthickness=0,
                    bg=square_color,
                    activebackground=square_color,
                    command=lambda r=row, c=col:
                    self.square_click(r, c),
                )

                button.place(
                    x=0,
                    y=0,
                    relwidth=1,
                    relheight=1,
                )

                row_squares.append(button)

            self.squares.append(row_squares)

        self.render_board()

    # ==========================================================
    # RENDER
    # ==========================================================

    def render_board(self):
        for row in range(self.BOARD_SIZE):
            for col in range(self.BOARD_SIZE):
                self.render_square(row, col)

    def render_square(self, row, col):
        button = self.squares[row][col]

        normal_color = self.get_square_color(row, col)

        # ------------------------------------------------------
        # Цвет клетки
        # ------------------------------------------------------

        if self.selected == (row, col):
            background = self.SELECTED_COLOR

        elif (row, col) in self.possible_moves:
            background = self.SELECTED_COLOR

        else:
            background = normal_color

        button.configure(
            bg=background,
            activebackground=background,
        )

        # ------------------------------------------------------
        # Фигура
        # ------------------------------------------------------

        piece = self.board[row][col]

        if piece is None:
            button.configure(
                image="",
                text="",
            )

        else:
            button.configure(
                image=self.images[piece],
                text="",
            )

    # ==========================================================
    # INPUT
    # ==========================================================

    def square_click(self, row, col):
        piece = self.board[row][col]

        # ------------------------------------------------------
        # Ничего не выбрано
        # ------------------------------------------------------

        if self.selected is None:

            if piece is None:
                return

            # Нельзя выбрать фигуру противника
            if not piece.startswith(self.turn):
                return

            self.selected = (row, col)

            self.possible_moves = self.get_possible_moves(
                row,
                col,
            )

            self.render_board()

            return

        # ------------------------------------------------------
        # Повторный клик по выбранной фигуре
        # ------------------------------------------------------

        if self.selected == (row, col):
            self.clear_selection()
            return

        # ------------------------------------------------------
        # Клик по другой своей фигуре
        # ------------------------------------------------------

        if piece is not None and piece.startswith(self.turn):
            self.selected = (row, col)

            self.possible_moves = self.get_possible_moves(
                row,
                col,
            )

            self.render_board()

            return

        # ------------------------------------------------------
        # Попытка сделать ход
        # ------------------------------------------------------

        if (row, col) in self.possible_moves:
            self.move_piece(row, col)

    # ==========================================================
    # MOVE
    # ==========================================================

    def move_piece(self, target_row, target_col):
        old_row, old_col = self.selected

        piece = self.board[old_row][old_col]

        self.board[target_row][target_col] = piece
        self.board[old_row][old_col] = None

        self.clear_selection()

        # Меняем сторону
        if self.turn == "w":
            self.turn = "b"
        else:
            self.turn = "w"

    # ==========================================================
    # MOVE VALIDATION
    # ==========================================================

    def get_possible_moves(self, row, col):
        piece = self.board[row][col]

        if piece is None:
            return []

        piece_type = piece[1]
        color = piece[0]

        if piece_type == "p":
            return self.get_pawn_moves(
                row,
                col,
                color,
            )

        if piece_type == "r":
            return self.get_rook_moves(
                row,
                col,
                color,
            )

        if piece_type == "n":
            return self.get_knight_moves(
                row,
                col,
                color,
            )

        if piece_type == "b":
            return self.get_bishop_moves(
                row,
                col,
                color,
            )

        if piece_type == "q":
            return self.get_queen_moves(
                row,
                col,
                color,
            )

        if piece_type == "k":
            return self.get_king_moves(
                row,
                col,
                color,
            )

        return []

    # ==========================================================
    # PAWN
    # ==========================================================

    def get_pawn_moves(self, row, col, color):
        moves = []

        direction = -1 if color == "w" else 1

        start_row = 6 if color == "w" else 1

        # ------------------------------------------------------
        # Движение на одну клетку
        # ------------------------------------------------------

        next_row = row + direction

        if self.is_inside_board(next_row, col):
            if self.board[next_row][col] is None:
                moves.append((next_row, col))

                # --------------------------------------------------
                # Движение на две клетки с начальной позиции
                # --------------------------------------------------

                if row == start_row:
                    next_next_row = row + direction * 2

                    if self.board[next_next_row][col] is None:
                        moves.append(
                            (next_next_row, col)
                        )

        # ------------------------------------------------------
        # Взятия
        # ------------------------------------------------------

        for dc in [-1, 1]:
            target_row = row + direction
            target_col = col + dc

            if not self.is_inside_board(
                target_row,
                target_col,
            ):
                continue

            target_piece = self.board[target_row][target_col]

            if (
                target_piece is not None
                and not target_piece.startswith(color)
            ):
                moves.append(
                    (target_row, target_col)
                )

        return moves

    # ==========================================================
    # ROOK
    # ==========================================================

    def get_rook_moves(self, row, col, color):
        directions = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
        ]

        return self.get_sliding_moves(
            row,
            col,
            color,
            directions,
        )

    # ==========================================================
    # BISHOP
    # ==========================================================

    def get_bishop_moves(self, row, col, color):
        directions = [
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ]

        return self.get_sliding_moves(
            row,
            col,
            color,
            directions,
        )

    # ==========================================================
    # QUEEN
    # ==========================================================

    def get_queen_moves(self, row, col, color):
        directions = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ]

        return self.get_sliding_moves(
            row,
            col,
            color,
            directions,
        )

    # ==========================================================
    # SLIDING PIECES
    # ==========================================================

    def get_sliding_moves(
        self,
        row,
        col,
        color,
        directions,
    ):
        moves = []

        for dr, dc in directions:

            current_row = row + dr
            current_col = col + dc

            while self.is_inside_board(
                current_row,
                current_col,
            ):
                target_piece = self.board[
                    current_row
                ][
                    current_col
                ]

                # Пустая клетка
                if target_piece is None:
                    moves.append(
                        (current_row, current_col)
                    )

                else:
                    # Фигура противника — можно взять
                    if not target_piece.startswith(color):
                        moves.append(
                            (current_row, current_col)
                        )

                    # Своя фигура — остановка
                    break

                current_row += dr
                current_col += dc

        return moves

    # ==========================================================
    # KNIGHT
    # ==========================================================

    def get_knight_moves(self, row, col, color):
        moves = []

        directions = [
            (-2, -1),
            (-2, 1),
            (-1, -2),
            (-1, 2),
            (1, -2),
            (1, 2),
            (2, -1),
            (2, 1),
        ]

        for dr, dc in directions:
            target_row = row + dr
            target_col = col + dc

            if not self.is_inside_board(
                target_row,
                target_col,
            ):
                continue

            target_piece = self.board[
                target_row
            ][
                target_col
            ]

            if target_piece is None:
                moves.append(
                    (target_row, target_col)
                )

            elif not target_piece.startswith(color):
                moves.append(
                    (target_row, target_col)
                )

        return moves

    # ==========================================================
    # KING
    # ==========================================================

    def get_king_moves(self, row, col, color):
        moves = []

        directions = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ]

        for dr, dc in directions:
            target_row = row + dr
            target_col = col + dc

            if not self.is_inside_board(
                target_row,
                target_col,
            ):
                continue

            target_piece = self.board[
                target_row
            ][
                target_col
            ]

            if target_piece is None:
                moves.append(
                    (target_row, target_col)
                )

            elif not target_piece.startswith(color):
                moves.append(
                    (target_row, target_col)
                )

        return moves

    # ==========================================================
    # HELPERS
    # ==========================================================

    @staticmethod
    def is_inside_board(row, col):
        return (
            0 <= row < Chess.BOARD_SIZE
            and 0 <= col < Chess.BOARD_SIZE
        )

    @staticmethod
    def get_square_color(row, col):
        if (row + col) % 2 == 0:
            return Chess.LIGHT_COLOR

        return Chess.DARK_COLOR

    def clear_selection(self):
        self.selected = None
        self.possible_moves = []

        self.render_board()


def main():
    root = tk.Tk()
    Chess(root)
    root.mainloop()


if __name__ == "__main__":
    main()