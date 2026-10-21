"""
Russian draughts (shashki) rules engine.

Board: 8x8, pieces live on dark squares ((row + col) % 2 == 1).
Row 0 is the top of the screen (black side), row 7 is the bottom (white side),
so a1 is board[7][0], exactly like in the chess driver.

Pieces are strings: colour + type, "wp" / "wk" / "bp" / "bk"
("p" = man, "k" = king).

Rules implemented:
  * White moves first, men move one square diagonally forward.
  * Capturing is mandatory. Men capture forward AND backward.
  * Kings are "flying": they move any distance along a diagonal
    and capture from a distance, landing on any free square behind the victim.
  * A capture must be continued while it is possible. The player may choose
    any capture sequence (not necessarily the longest).
  * Captured pieces are removed only after the whole move is finished and
    cannot be jumped twice (the "Turkish strike" rule).
  * A man that reaches the far row during a capture becomes a king at once
    and keeps capturing as a king.
  * A player with no pieces or no legal moves loses.
  * Draw: 15 moves by each side with only kings moving and no captures,
    or the same position for the third time.

A move is a dict:
    {"path": [(row, col), ...],      # start square + every landing square
     "captures": [(row, col), ...],  # squares of the captured pieces
     "promotion": bool}              # the man becomes a king by this move
"""


class Checkers:
    BOARD_SIZE = 8

    PIECE_NAMES = {
        "p": "Man",
        "k": "King",
    }

    PIECE_SYMBOLS = {
        "p": "●",
        "k": "♛",
    }

    DIRECTIONS = ((-1, -1), (-1, 1), (1, -1), (1, 1))

    # 15 moves by each side = 30 plies
    DRAW_KING_PLIES = 30

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

        # Pieces of the given colour that have been captured.
        self.captured_pieces = {
            "w": [],
            "b": [],
        }

        self.game_over = False

        # Plies since the last capture or man move.
        self.quiet_plies = 0

        self.position_counts = {}
        self._register_position()

        # States before every real move.
        self.state_history = []

    def save_state(self):
        self.state_history.append({
            "board": self.copy_board(self.board),
            "turn": self.turn,
            "last_move": self.last_move,
            "move_history": list(self.move_history),
            "captured_pieces": {
                "w": list(self.captured_pieces["w"]),
                "b": list(self.captured_pieces["b"]),
            },
            "game_over": self.game_over,
            "quiet_plies": self.quiet_plies,
            "position_counts": dict(self.position_counts),
        })

    def undo(self):
        if not self.state_history:
            return False

        state = self.state_history.pop()

        self.board = state["board"]
        self.turn = state["turn"]
        self.last_move = state["last_move"]
        self.move_history = state["move_history"]
        self.captured_pieces = state["captured_pieces"]
        self.game_over = state["game_over"]
        self.quiet_plies = state["quiet_plies"]
        self.position_counts = state["position_counts"]

        return True

    def copy(self):
        """
        Lightweight copy (no undo history), enough for analysis.
        """
        new_game = Checkers()

        new_game.board = self.copy_board(self.board)
        new_game.turn = self.turn
        new_game.last_move = self.last_move
        new_game.move_history = list(self.move_history)
        new_game.captured_pieces = {
            "w": list(self.captured_pieces["w"]),
            "b": list(self.captured_pieces["b"]),
        }
        new_game.game_over = self.game_over
        new_game.quiet_plies = self.quiet_plies
        new_game.position_counts = dict(self.position_counts)
        new_game.state_history = []

        return new_game

    @staticmethod
    def copy_board(board):
        return [row[:] for row in board]

    def create_initial_board(self):
        board = [[None] * 8 for _ in range(8)]

        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 0:
                    continue

                if row < 3:
                    board[row][col] = "bp"
                elif row > 4:
                    board[row][col] = "wp"

        return board

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

    @staticmethod
    def promotion_row(color):
        return 0 if color == "w" else 7

    def _position_key(self):
        return (
            tuple(tuple(row) for row in self.board),
            self.turn,
        )

    def _register_position(self):
        key = self._position_key()
        self.position_counts[key] = self.position_counts.get(key, 0) + 1

    # =========================================================
    # MOVE GENERATION (static, work on any board)
    # =========================================================

    @classmethod
    def generate_moves(cls, board, color):
        """
        All legal moves for `color`.
        If any capture exists, only captures are returned (mandatory capture).
        """
        captures = []

        for row in range(8):
            for col in range(8):
                piece = board[row][col]

                if piece is not None and piece[0] == color:
                    captures.extend(cls.piece_captures(board, row, col))

        if captures:
            return captures

        quiet = []

        for row in range(8):
            for col in range(8):
                piece = board[row][col]

                if piece is not None and piece[0] == color:
                    quiet.extend(cls.piece_quiet_moves(board, row, col))

        return quiet

    @classmethod
    def piece_quiet_moves(cls, board, row, col):
        piece = board[row][col]
        color = piece[0]
        moves = []

        if piece[1] == "k":
            for dr, dc in cls.DIRECTIONS:
                r, c = row + dr, col + dc

                while cls.inside_board(r, c) and board[r][c] is None:
                    moves.append({
                        "path": [(row, col), (r, c)],
                        "captures": [],
                        "promotion": False,
                    })

                    r += dr
                    c += dc

            return moves

        forward = -1 if color == "w" else 1
        promo_row = cls.promotion_row(color)

        for dc in (-1, 1):
            r, c = row + forward, col + dc

            if cls.inside_board(r, c) and board[r][c] is None:
                moves.append({
                    "path": [(row, col), (r, c)],
                    "captures": [],
                    "promotion": r == promo_row,
                })

        return moves

    @classmethod
    def piece_captures(cls, board, row, col):
        """
        All complete capture sequences of the piece on (row, col).
        """
        piece = board[row][col]
        color = piece[0]
        is_king = piece[1] == "k"

        results = []

        # Lift the piece off the board: its start square counts as free,
        # so a long capture may pass over it or even land on it.
        board[row][col] = None

        try:
            cls._capture_search(
                board,
                color,
                row,
                col,
                is_king,
                is_king,
                [(row, col)],
                [],
                results,
            )
        finally:
            board[row][col] = piece

        return results

    @classmethod
    def _capture_search(
        cls,
        board,
        color,
        row,
        col,
        is_king,
        started_as_king,
        path,
        captured,
        results,
    ):
        promo_row = cls.promotion_row(color)

        for dr, dc in cls.DIRECTIONS:

            if is_king:
                r, c = row + dr, col + dc

                while cls.inside_board(r, c) and board[r][c] is None:
                    r += dr
                    c += dc

                if not cls.inside_board(r, c):
                    continue

                target = board[r][c]

                # Own piece, or a piece that was already jumped in this move.
                if target[0] == color or (r, c) in captured:
                    continue

                landings = []
                lr, lc = r + dr, c + dc

                while cls.inside_board(lr, lc) and board[lr][lc] is None:
                    landings.append((lr, lc))
                    lr += dr
                    lc += dc

                if not landings:
                    continue

                new_captured = captured + [(r, c)]

                # If at least one landing square allows a further capture,
                # the capture must be continued from one of those squares.
                continuing = [
                    square
                    for square in landings
                    if cls._has_capture(
                        board, color, square[0], square[1], True, new_captured
                    )
                ]

                if continuing:
                    for lr, lc in continuing:
                        cls._capture_search(
                            board, color, lr, lc, True, started_as_king,
                            path + [(lr, lc)], new_captured, results,
                        )
                else:
                    for lr, lc in landings:
                        results.append({
                            "path": path + [(lr, lc)],
                            "captures": new_captured,
                            "promotion": not started_as_king and is_king,
                        })

            else:
                mr, mc = row + dr, col + dc
                lr, lc = row + 2 * dr, col + 2 * dc

                if not cls.inside_board(lr, lc):
                    continue

                target = board[mr][mc]

                if target is None or target[0] == color:
                    continue

                if (mr, mc) in captured:
                    continue

                if board[lr][lc] is not None:
                    continue

                new_captured = captured + [(mr, mc)]

                # A man reaching the far row becomes a king immediately.
                becomes_king = lr == promo_row

                if cls._has_capture(
                    board, color, lr, lc, becomes_king, new_captured
                ):
                    cls._capture_search(
                        board, color, lr, lc, becomes_king, started_as_king,
                        path + [(lr, lc)], new_captured, results,
                    )
                else:
                    results.append({
                        "path": path + [(lr, lc)],
                        "captures": new_captured,
                        "promotion": becomes_king,
                    })

    @classmethod
    def _has_capture(cls, board, color, row, col, is_king, captured):
        """
        Is there at least one capture from (row, col)?
        """
        for dr, dc in cls.DIRECTIONS:

            if is_king:
                r, c = row + dr, col + dc

                while cls.inside_board(r, c) and board[r][c] is None:
                    r += dr
                    c += dc

                if not cls.inside_board(r, c):
                    continue

                target = board[r][c]

                if target[0] == color or (r, c) in captured:
                    continue

                lr, lc = r + dr, c + dc

                if cls.inside_board(lr, lc) and board[lr][lc] is None:
                    return True

            else:
                mr, mc = row + dr, col + dc
                lr, lc = row + 2 * dr, col + 2 * dc

                if not cls.inside_board(lr, lc):
                    continue

                target = board[mr][mc]

                if target is None or target[0] == color:
                    continue

                if (mr, mc) in captured:
                    continue

                if board[lr][lc] is None:
                    return True

        return False

    @staticmethod
    def apply_move_to_board(board, move):
        """
        Applies a move to a board in place (no turn / history handling).
        """
        start_row, start_col = move["path"][0]
        end_row, end_col = move["path"][-1]

        piece = board[start_row][start_col]

        board[start_row][start_col] = None

        for row, col in move["captures"]:
            board[row][col] = None

        if move["promotion"]:
            piece = piece[0] + "k"

        board[end_row][end_col] = piece

    # =========================================================
    # LEGAL MOVES (instance API)
    # =========================================================

    def get_all_legal_moves(self, color=None):
        return self.generate_moves(self.board, color or self.turn)

    def get_legal_moves(self, row, col):
        """
        Legal moves of the piece on (row, col), taking the mandatory
        capture rule into account (may be empty even for a free piece).
        """
        piece = self.board[row][col]

        if piece is None:
            return []

        return [
            move
            for move in self.generate_moves(self.board, piece[0])
            if move["path"][0] == (row, col)
        ]

    def has_forced_capture(self, color=None):
        moves = self.get_all_legal_moves(color)

        return bool(moves) and bool(moves[0]["captures"])

    def pieces_that_must_capture(self, color=None):
        moves = self.get_all_legal_moves(color)

        if not moves or not moves[0]["captures"]:
            return set()

        return {move["path"][0] for move in moves}

    # =========================================================
    # MOVE EXECUTION
    # =========================================================

    def find_legal_move(self, move_or_path):
        """
        Accepts a move dict or a path (list of squares).
        Returns the matching legal move or None.
        """
        if isinstance(move_or_path, dict):
            path = move_or_path["path"]
        else:
            path = move_or_path

        path = [tuple(square) for square in path]

        if not path:
            return None

        start_row, start_col = path[0]

        for move in self.get_legal_moves(start_row, start_col):
            if move["path"] == path:
                return move

        return None

    def make_move(self, move_or_path):
        if self.game_over:
            return False

        start = (
            move_or_path["path"][0]
            if isinstance(move_or_path, dict)
            else tuple(move_or_path[0])
        )

        piece = self.board[start[0]][start[1]]

        if piece is None or piece[0] != self.turn:
            return False

        move = self.find_legal_move(move_or_path)

        if move is None:
            return False

        # Save state only after the move has been confirmed as legal.
        self.save_state()

        color = piece[0]

        captured_pieces = [
            self.board[row][col]
            for row, col in move["captures"]
        ]

        self.apply_move_to_board(self.board, move)

        for captured in captured_pieces:
            self.captured_pieces[captured[0]].append(captured)

        self.last_move = {
            "piece": piece,
            "from": move["path"][0],
            "to": move["path"][-1],
            "path": list(move["path"]),
            "captures": list(move["captures"]),
            "captured": captured_pieces,
            "promotion": move["promotion"],
        }

        self.move_history.append(self.get_move_notation(self.last_move))

        if move["captures"] or piece[1] == "p":
            self.quiet_plies = 0
        else:
            self.quiet_plies += 1

        self.turn = self.opposite_color(color)

        self._register_position()

        return True

    # =========================================================
    # NOTATION
    # =========================================================

    def square_to_notation(self, row, col):
        return f"{'abcdefgh'[col]}{8 - row}"

    def get_move_notation(self, move):
        squares = [
            self.square_to_notation(row, col)
            for row, col in move["path"]
        ]

        separator = ":" if move["captures"] else "-"

        return separator.join(squares)

    # =========================================================
    # GAME STATE
    # =========================================================

    def check_game_state(self):
        """
        None while the game goes on, otherwise a result dict.
        """
        color = self.turn

        moves = self.get_all_legal_moves(color)

        if not moves:
            has_pieces = any(
                piece is not None and piece[0] == color
                for row in self.board
                for piece in row
            )

            self.game_over = True

            return {
                "type": "win",
                "reason": "no_moves" if has_pieces else "no_pieces",
                "winner": self.opposite_color(color),
                "loser": color,
            }

        if self.quiet_plies >= self.DRAW_KING_PLIES:
            self.game_over = True

            return {
                "type": "draw",
                "reason": "kings_only",
                "winner": None,
                "loser": None,
            }

        if self.position_counts.get(self._position_key(), 0) >= 3:
            self.game_over = True

            return {
                "type": "draw",
                "reason": "repetition",
                "winner": None,
                "loser": None,
            }

        return None

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

    def count_pieces(self, color):
        return sum(
            1
            for row in self.board
            for piece in row
            if piece is not None and piece[0] == color
        )
