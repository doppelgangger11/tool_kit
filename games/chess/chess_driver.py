from copy import deepcopy


class Chess:
    BOARD_SIZE = 8

    PIECE_NAMES = {
        "p": "Pawn",
        "n": "Knight",
        "b": "Bishop",
        "r": "Rook",
        "q": "Queen",
        "k": "King",
    }

    PIECE_SYMBOLS = {
        "p": "♟",
        "n": "♞",
        "b": "♝",
        "r": "♜",
        "q": "♛",
        "k": "♚",
    }

    def __init__(self):
        self.reset()

    # =========================================================
    # GAME STATE
    # =========================================================

    def reset(self):
        self.board = self.create_initial_board()

        self.turn = "w"
        self.last_move = None

        self.move_history = []

        self.captured_pieces = {
            "w": [],
            "b": [],
        }

        self.game_over = False

        self.castling_rights = {
            "w": {
                "king": True,
                "kingside": True,
                "queenside": True,
            },
            "b": {
                "king": True,
                "kingside": True,
                "queenside": True,
            },
        }

    def create_initial_board(self):
        return [
            ["br", "bn", "bb", "bq", "bk", "bb", "bn", "br"],
            ["bp", "bp", "bp", "bp", "bp", "bp", "bp", "bp"],
            [None, None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None],
            ["wp", "wp", "wp", "wp", "wp", "wp", "wp", "wp"],
            ["wr", "wn", "wb", "wq", "wk", "wb", "wn", "wr"],
        ]

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def inside_board(row, col):
        return 0 <= row < 8 and 0 <= col < 8

    @staticmethod
    def opposite_color(color):
        return "b" if color == "w" else "w"

    @staticmethod
    def piece_color(piece):
        return piece[0] if piece else None

    @staticmethod
    def piece_type(piece):
        return piece[1] if piece else None

    # =========================================================
    # MOVE GENERATION
    # =========================================================

    def get_possible_moves(self, row, col):
        piece = self.board[row][col]

        if piece is None:
            return []

        color = piece[0]
        piece_type = piece[1]

        if piece_type == "p":
            return self.get_pawn_moves(row, col, color)

        if piece_type == "r":
            return self.get_rook_moves(row, col, color)

        if piece_type == "n":
            return self.get_knight_moves(row, col, color)

        if piece_type == "b":
            return self.get_bishop_moves(row, col, color)

        if piece_type == "q":
            return self.get_queen_moves(row, col, color)

        if piece_type == "k":
            return self.get_king_moves(row, col, color)

        return []

    # ---------------------------------------------------------
    # PAWN
    # ---------------------------------------------------------

    def get_pawn_moves(self, row, col, color):
        moves = []

        direction = -1 if color == "w" else 1
        start_row = 6 if color == "w" else 1

        # Forward one
        new_row = row + direction

        if self.inside_board(new_row, col):
            if self.board[new_row][col] is None:
                moves.append((new_row, col))

                # Forward two
                if row == start_row:
                    two_row = row + 2 * direction

                    if self.board[two_row][col] is None:
                        moves.append((two_row, col))

        # Captures
        for delta_col in (-1, 1):
            new_col = col + delta_col

            if not self.inside_board(new_row, new_col):
                continue

            target = self.board[new_row][new_col]

            if target is not None and target[0] != color:
                moves.append((new_row, new_col))

        return moves

    # ---------------------------------------------------------
    # ROOK
    # ---------------------------------------------------------

    def get_rook_moves(self, row, col, color):
        return self.get_sliding_moves(
            row,
            col,
            color,
            [
                (-1, 0),
                (1, 0),
                (0, -1),
                (0, 1),
            ],
        )

    # ---------------------------------------------------------
    # BISHOP
    # ---------------------------------------------------------

    def get_bishop_moves(self, row, col, color):
        return self.get_sliding_moves(
            row,
            col,
            color,
            [
                (-1, -1),
                (-1, 1),
                (1, -1),
                (1, 1),
            ],
        )

    # ---------------------------------------------------------
    # QUEEN
    # ---------------------------------------------------------

    def get_queen_moves(self, row, col, color):
        return self.get_sliding_moves(
            row,
            col,
            color,
            [
                (-1, 0),
                (1, 0),
                (0, -1),
                (0, 1),
                (-1, -1),
                (-1, 1),
                (1, -1),
                (1, 1),
            ],
        )

    # ---------------------------------------------------------
    # KNIGHT
    # ---------------------------------------------------------

    def get_knight_moves(self, row, col, color):
        moves = []

        offsets = [
            (-2, -1),
            (-2, 1),
            (-1, -2),
            (-1, 2),
            (1, -2),
            (1, 2),
            (2, -1),
            (2, 1),
        ]

        for dr, dc in offsets:
            new_row = row + dr
            new_col = col + dc

            if not self.inside_board(new_row, new_col):
                continue

            target = self.board[new_row][new_col]

            if target is None or target[0] != color:
                moves.append((new_row, new_col))

        return moves

    # ---------------------------------------------------------
    # KING
    # ---------------------------------------------------------

    def get_king_moves(self, row, col, color):
        moves = []

        offsets = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ]

        for dr, dc in offsets:
            new_row = row + dr
            new_col = col + dc

            if not self.inside_board(new_row, new_col):
                continue

            target = self.board[new_row][new_col]

            if target is None or target[0] != color:
                moves.append((new_row, new_col))

        return moves

    # ---------------------------------------------------------
    # SLIDING PIECES
    # ---------------------------------------------------------

    def get_sliding_moves(self, row, col, color, directions):
        moves = []

        for dr, dc in directions:
            current_row = row + dr
            current_col = col + dc

            while self.inside_board(current_row, current_col):
                target = self.board[current_row][current_col]

                if target is None:
                    moves.append((current_row, current_col))

                else:
                    if target[0] != color:
                        moves.append((current_row, current_col))

                    break

                current_row += dr
                current_col += dc

        return moves

    # =========================================================
    # CHECK / ATTACKS
    # =========================================================

    def find_king(self, color):
        for row in range(8):
            for col in range(8):
                if self.board[row][col] == color + "k":
                    return row, col

        return None

    def is_square_attacked(self, row, col, by_color):
        # Pawn attacks
        pawn_row = row + (1 if by_color == "w" else -1)

        for pawn_col in (col - 1, col + 1):
            if self.inside_board(pawn_row, pawn_col):
                if self.board[pawn_row][pawn_col] == by_color + "p":
                    return True

        # Knight attacks
        knight_offsets = [
            (-2, -1),
            (-2, 1),
            (-1, -2),
            (-1, 2),
            (1, -2),
            (1, 2),
            (2, -1),
            (2, 1),
        ]

        for dr, dc in knight_offsets:
            r = row + dr
            c = col + dc

            if self.inside_board(r, c):
                if self.board[r][c] == by_color + "n":
                    return True

        # King attacks
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue

                r = row + dr
                c = col + dc

                if self.inside_board(r, c):
                    if self.board[r][c] == by_color + "k":
                        return True

        # Rook / Queen
        rook_directions = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
        ]

        for dr, dc in rook_directions:
            r = row + dr
            c = col + dc

            while self.inside_board(r, c):
                piece = self.board[r][c]

                if piece is None:
                    r += dr
                    c += dc
                    continue

                if piece[0] == by_color:
                    if piece[1] in ("r", "q"):
                        return True

                break

        # Bishop / Queen
        bishop_directions = [
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ]

        for dr, dc in bishop_directions:
            r = row + dr
            c = col + dc

            while self.inside_board(r, c):
                piece = self.board[r][c]

                if piece is None:
                    r += dr
                    c += dc
                    continue

                if piece[0] == by_color:
                    if piece[1] in ("b", "q"):
                        return True

                break

        return False

    def is_in_check(self, color):
        king_position = self.find_king(color)

        if king_position is None:
            return False

        row, col = king_position
        opponent = self.opposite_color(color)

        return self.is_square_attacked(row, col, opponent)

    # =========================================================
    # CASTLING
    # =========================================================

    def get_castling_moves(self, row, col, color):
        moves = []

        if self.board[row][col] != color + "k":
            return moves

        if self.is_in_check(color):
            return moves

        opponent = self.opposite_color(color)

        home_row = 7 if color == "w" else 0

        # King side
        if (
            row == home_row
            and col == 4
            and self.castling_rights[color]["king"]
            and self.castling_rights[color]["kingside"]
        ):
            if (
                self.board[home_row][5] is None
                and self.board[home_row][6] is None
                and self.board[home_row][7] == color + "r"
            ):
                if (
                    not self.is_square_attacked(home_row, 5, opponent)
                    and not self.is_square_attacked(home_row, 6, opponent)
                ):
                    moves.append((home_row, 6))

        # Queen side
        if (
            row == home_row
            and col == 4
            and self.castling_rights[color]["king"]
            and self.castling_rights[color]["queenside"]
        ):
            if (
                self.board[home_row][1] is None
                and self.board[home_row][2] is None
                and self.board[home_row][3] is None
                and self.board[home_row][0] == color + "r"
            ):
                if (
                    not self.is_square_attacked(home_row, 3, opponent)
                    and not self.is_square_attacked(home_row, 2, opponent)
                ):
                    moves.append((home_row, 2))

        return moves

    def move_castling_rook(self, row, king_from_col, king_to_col):
        color = self.board[row][king_to_col][0]

        if king_to_col > king_from_col:
            # O-O
            rook_from_col = 7
            rook_to_col = 5
        else:
            # O-O-O
            rook_from_col = 0
            rook_to_col = 3

        rook = self.board[row][rook_from_col]

        self.board[row][rook_from_col] = None
        self.board[row][rook_to_col] = rook

    # =========================================================
    # CASTLING RIGHTS
    # =========================================================

    def disable_rook_castling(self, color, row, col):
        home_row = 7 if color == "w" else 0

        if row != home_row:
            return

        if col == 0:
            self.castling_rights[color]["queenside"] = False

        elif col == 7:
            self.castling_rights[color]["kingside"] = False

    def update_castling_rights(
        self,
        piece,
        from_row,
        from_col,
        to_row,
        to_col,
        captured_piece,
    ):
        color = piece[0]
        piece_type = piece[1]

        # King moved
        if piece_type == "k":
            self.castling_rights[color]["king"] = False
            self.castling_rights[color]["kingside"] = False
            self.castling_rights[color]["queenside"] = False

        # Rook moved
        if piece_type == "r":
            self.disable_rook_castling(
                color,
                from_row,
                from_col,
            )

        # Rook captured
        if captured_piece is not None and captured_piece[1] == "r":
            self.disable_rook_castling(
                captured_piece[0],
                to_row,
                to_col,
            )

    # =========================================================
    # EN PASSANT
    # =========================================================

    def get_en_passant_moves(self, row, col, color):
        moves = []

        if self.last_move is None:
            return moves

        piece = self.board[row][col]

        if piece != color + "p":
            return moves

        last_piece = self.last_move["piece"]

        if last_piece != self.opposite_color(color) + "p":
            return moves

        from_row, from_col = self.last_move["from"]
        to_row, to_col = self.last_move["to"]

        # Last move must have been a two-square pawn move
        if abs(to_row - from_row) != 2:
            return moves

        # Pawn must now be next to us
        if to_row != row:
            return moves

        if abs(to_col - col) != 1:
            return moves

        # Target square must be empty
        direction = -1 if color == "w" else 1
        target_row = row + direction

        if self.board[target_row][to_col] is not None:
            return moves

        moves.append((target_row, to_col))

        return moves

    # =========================================================
    # LEGAL MOVES
    # =========================================================

    def get_legal_moves(self, row, col):
        piece = self.board[row][col]

        if piece is None:
            return []

        color = piece[0]

        moves = self.get_possible_moves(row, col)

        # Castling
        if piece[1] == "k":
            moves.extend(
                self.get_castling_moves(
                    row,
                    col,
                    color,
                )
            )

        # En passant
        if piece[1] == "p":
            moves.extend(
                self.get_en_passant_moves(
                    row,
                    col,
                    color,
                )
            )

        # Remove duplicates
        moves = list(dict.fromkeys(moves))

        legal_moves = []

        for target_row, target_col in moves:
            original_board = deepcopy(self.board)

            captured_piece = self.board[target_row][target_col]

            is_en_passant = (
                piece[1] == "p"
                and target_col != col
                and captured_piece is None
            )

            en_passant_captured = None

            if is_en_passant:
                captured_row = target_row + (
                    1 if color == "w" else -1
                )

                en_passant_captured = self.board[captured_row][target_col]

                self.board[captured_row][target_col] = None

            # Move piece
            self.board[target_row][target_col] = piece
            self.board[row][col] = None

            # Move rook for castling
            is_castling = (
                piece[1] == "k"
                and abs(target_col - col) == 2
            )

            if is_castling:
                if target_col > col:
                    rook_from = 7
                    rook_to = 5
                else:
                    rook_from = 0
                    rook_to = 3

                rook = self.board[row][rook_from]

                self.board[row][rook_from] = None
                self.board[row][rook_to] = rook

            if not self.is_in_check(color):
                legal_moves.append((target_row, target_col))

            self.board = original_board

        return legal_moves

    # =========================================================
    # MOVE EXECUTION
    # =========================================================

    def move_piece(
        self,
        from_row,
        from_col,
        to_row,
        to_col,
        promotion_piece=None,
    ):
        if self.game_over:
            return False

        piece = self.board[from_row][from_col]

        if piece is None:
            return False

        if piece[0] != self.turn:
            return False

        legal_moves = self.get_legal_moves(
            from_row,
            from_col,
        )

        if (to_row, to_col) not in legal_moves:
            return False

        color = piece[0]
        piece_type = piece[1]

        captured_piece = self.board[to_row][to_col]

        is_castling = (
            piece_type == "k"
            and abs(to_col - from_col) == 2
        )

        is_en_passant = (
            piece_type == "p"
            and to_col != from_col
            and captured_piece is None
        )

        # -----------------------------------------------------
        # Update castling rights
        # -----------------------------------------------------

        self.update_castling_rights(
            piece,
            from_row,
            from_col,
            to_row,
            to_col,
            captured_piece,
        )

        # -----------------------------------------------------
        # En passant capture
        # -----------------------------------------------------

        if is_en_passant:
            captured_row = to_row + (
                1 if color == "w" else -1
            )

            captured_piece = self.board[captured_row][to_col]

            self.board[captured_row][to_col] = None

        # -----------------------------------------------------
        # Move piece
        # -----------------------------------------------------

        self.board[from_row][from_col] = None
        self.board[to_row][to_col] = piece

        # -----------------------------------------------------
        # Castling rook
        # -----------------------------------------------------

        if is_castling:
            self.move_castling_rook(
                to_row,
                from_col,
                to_col,
            )

        # -----------------------------------------------------
        # Capture
        # -----------------------------------------------------

        if captured_piece is not None:
            self.captured_pieces[captured_piece[0]].append(
                captured_piece
            )

        # -----------------------------------------------------
        # Promotion
        # -----------------------------------------------------

        promoted_piece = None

        if piece_type == "p":
            if to_row == 0 or to_row == 7:
                promoted_piece = promotion_piece or "q"

                if promoted_piece not in (
                    "q",
                    "r",
                    "b",
                    "n",
                ):
                    promoted_piece = "q"

                self.board[to_row][to_col] = (
                    color + promoted_piece
                )

        # -----------------------------------------------------
        # Save move
        # -----------------------------------------------------

        self.last_move = {
            "piece": piece,
            "from": (from_row, from_col),
            "to": (to_row, to_col),
            "captured": captured_piece,
            "castling": is_castling,
            "en_passant": is_en_passant,
            "promotion": promoted_piece,
        }

        notation = self.get_move_notation(
            self.last_move
        )

        self.move_history.append(notation)

        # -----------------------------------------------------
        # Next turn
        # -----------------------------------------------------

        self.turn = self.opposite_color(self.turn)

        return True

    # =========================================================
    # MOVE NOTATION
    # =========================================================

    def square_to_notation(self, row, col):
        files = "abcdefgh"

        return f"{files[col]}{8 - row}"

    def get_move_notation(self, move):
        piece = move["piece"]
        piece_type = piece[1]

        from_row, from_col = move["from"]
        to_row, to_col = move["to"]

        captured = move["captured"]
        promotion = move["promotion"]

        # Castling
        if move["castling"]:
            if to_col > from_col:
                return "O-O"

            return "O-O-O"

        target_square = self.square_to_notation(
            to_row,
            to_col,
        )

        # Pawn
        if piece_type == "p":
            if captured is not None:
                notation = (
                    "abcdefgh"[from_col]
                    + "x"
                    + target_square
                )
            else:
                notation = target_square

            if promotion:
                notation += "=" + promotion.upper()

            return notation

        # Other pieces
        piece_letter = piece_type.upper()

        capture_symbol = "x" if captured else ""

        return (
            piece_letter
            + capture_symbol
            + target_square
        )

    # =========================================================
    # GAME STATE
    # =========================================================

    def check_game_state(self):
        color = self.turn

        has_legal_move = False

        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]

                if piece is None:
                    continue

                if piece[0] != color:
                    continue

                if self.get_legal_moves(row, col):
                    has_legal_move = True
                    break

            if has_legal_move:
                break

        if has_legal_move:
            return None

        if self.is_in_check(color):
            self.game_over = True

            return {
                "type": "checkmate",
                "winner": self.opposite_color(color),
                "loser": color,
            }

        self.game_over = True

        return {
            "type": "stalemate",
            "winner": None,
            "loser": None,
        }

    # =========================================================
    # UTILITY
    # =========================================================

    def get_piece_symbol(self, piece):
        if piece is None:
            return ""

        return self.PIECE_SYMBOLS[piece[1]]

    def get_piece_name(self, piece):
        if piece is None:
            return ""

        return self.PIECE_NAMES[piece[1]]