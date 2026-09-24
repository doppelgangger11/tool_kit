import random


class ChessBot:
    PIECE_VALUES = {
        "p": 100,
        "n": 320,
        "b": 330,
        "r": 500,
        "q": 900,
        "k": 20000,
    }

    DIFFICULTIES = {
        "Easy": {
            "depth": 0,
            "randomness": 0.35,
        },
        "Medium": {
            "depth": 2,
            "randomness": 0.10,
        },
        "Hard": {
            "depth": 3,
            "randomness": 0.03,
        },
        "Expert": {
            "depth": 4,
            "randomness": 0.00,
        },
    }

    # Positive values mean good for White.
    PAWN_TABLE = [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [50, 50, 50, 50, 50, 50, 50, 50],
        [10, 10, 20, 30, 30, 20, 10, 10],
        [5, 5, 10, 25, 25, 10, 5, 5],
        [0, 0, 0, 20, 20, 0, 0, 0],
        [5, -5, -10, 0, 0, -10, -5, 5],
        [5, 10, 10, -20, -20, 10, 10, 5],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ]

    KNIGHT_TABLE = [
        [-50, -40, -30, -30, -30, -30, -40, -50],
        [-40, -20, 0, 0, 0, 0, -20, -40],
        [-30, 0, 10, 15, 15, 10, 0, -30],
        [-30, 5, 15, 20, 20, 15, 5, -30],
        [-30, 0, 15, 20, 20, 15, 0, -30],
        [-30, 5, 10, 15, 15, 10, 5, -30],
        [-40, -20, 0, 5, 5, 0, -20, -40],
        [-50, -40, -30, -30, -30, -30, -40, -50],
    ]

    BISHOP_TABLE = [
        [-20, -10, -10, -10, -10, -10, -10, -20],
        [-10, 0, 0, 0, 0, 0, 0, -10],
        [-10, 0, 5, 10, 10, 5, 0, -10],
        [-10, 5, 5, 10, 10, 5, 5, -10],
        [-10, 0, 10, 10, 10, 10, 0, -10],
        [-10, 10, 10, 10, 10, 10, 10, -10],
        [-10, 5, 0, 0, 0, 0, 5, -10],
        [-20, -10, -10, -10, -10, -10, -10, -20],
    ]

    ROOK_TABLE = [
        [0, 0, 0, 5, 5, 0, 0, 0],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [5, 10, 10, 10, 10, 10, 10, 5],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ]

    QUEEN_TABLE = [
        [-20, -10, -10, 0, 0, -10, -10, -20],
        [-10, 0, 0, 0, 0, 0, 0, -10],
        [-10, 0, 5, 5, 5, 5, 0, -10],
        [0, 0, 5, 5, 5, 5, 0, -5],
        [-5, 0, 5, 5, 5, 5, 0, -5],
        [-10, 5, 5, 5, 5, 5, 0, -10],
        [-10, 0, 5, 0, 0, 0, 0, -10],
        [-20, -10, -10, 0, 0, -10, -10, -20],
    ]

    KING_TABLE = [
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-20, -30, -30, -40, -40, -30, -30, -20],
        [-10, -20, -20, -20, -20, -20, -20, -10],
        [20, 20, 0, 0, 0, 0, 20, 20],
        [20, 30, 10, 0, 0, 10, 30, 20],
    ]

    TABLES = {
        "p": PAWN_TABLE,
        "n": KNIGHT_TABLE,
        "b": BISHOP_TABLE,
        "r": ROOK_TABLE,
        "q": QUEEN_TABLE,
        "k": KING_TABLE,
    }

    def __init__(self, color="b", difficulty="Medium"):
        self.color = color

        if difficulty not in self.DIFFICULTIES:
            difficulty = "Medium"

        self.difficulty = difficulty

        self.depth = self.DIFFICULTIES[
            difficulty
        ]["depth"]

        self.randomness = self.DIFFICULTIES[
            difficulty
        ]["randomness"]

    # =========================================================
    # PUBLIC API
    # =========================================================

    def make_move(self, game):
        if game.game_over:
            return None

        if game.turn != self.color:
            return None

        moves = self.get_all_moves(game, self.color)

        if not moves:
            return None

        # Easy
        if self.depth == 0:
            return self.choose_easy_move(
                game,
                moves,
            )

        best_move = self.find_best_move(
            game,
            moves,
        )

        return best_move

    # =========================================================
    # MOVE GENERATION
    # =========================================================

    def get_all_moves(self, game, color):
        moves = []

        for row in range(8):
            for col in range(8):
                piece = game.board[row][col]

                if piece is None:
                    continue

                if piece[0] != color:
                    continue

                legal_moves = game.get_legal_moves(
                    row,
                    col,
                )

                for target_row, target_col in legal_moves:
                    # Promotion creates four possible moves.
                    if (
                        piece[1] == "p"
                        and target_row in (0, 7)
                    ):
                        for promotion in (
                            "q",
                            "r",
                            "b",
                            "n",
                        ):
                            moves.append(
                                (
                                    row,
                                    col,
                                    target_row,
                                    target_col,
                                    promotion,
                                )
                            )
                    else:
                        moves.append(
                            (
                                row,
                                col,
                                target_row,
                                target_col,
                                None,
                            )
                        )

        return moves

    # =========================================================
    # EASY
    # =========================================================

    def choose_easy_move(self, game, moves):
        capture_moves = []

        for move in moves:
            if self.is_capture(game, move):
                capture_moves.append(move)

        if capture_moves and random.random() > 0.35:
            return random.choice(capture_moves)

        return random.choice(moves)

    # =========================================================
    # BEST MOVE
    # =========================================================

    def find_best_move(self, game, moves):
        random.shuffle(moves)

        best_score = float("-inf")
        best_moves = []

        alpha = float("-inf")
        beta = float("inf")

        for move in moves:
            simulation = game.copy()

            self.apply_move(
                simulation,
                move,
            )

            score = self.minimax(
                simulation,
                self.depth - 1,
                alpha,
                beta,
                maximizing=False,
            )

            if score > best_score:
                best_score = score
                best_moves = [move]

            elif score == best_score:
                best_moves.append(move)

            alpha = max(alpha, best_score)

        if not best_moves:
            return random.choice(moves)

        if self.randomness > 0:
            if random.random() < self.randomness:
                return random.choice(moves)

        return random.choice(best_moves)

    # =========================================================
    # MINIMAX
    # =========================================================

    def minimax(
        self,
        game,
        depth,
        alpha,
        beta,
        maximizing,
    ):
        terminal = self.get_terminal_score(
            game,
            depth,
        )

        if terminal is not None:
            return terminal

        if depth <= 0:
            return self.evaluate(game)

        color = game.turn

        moves = self.get_all_moves(
            game,
            color,
        )

        if not moves:
            return self.evaluate(game)

        if maximizing:
            best_score = float("-inf")

            for move in moves:
                simulation = game.copy()

                self.apply_move(
                    simulation,
                    move,
                )

                score = self.minimax(
                    simulation,
                    depth - 1,
                    alpha,
                    beta,
                    False,
                )

                best_score = max(
                    best_score,
                    score,
                )

                alpha = max(
                    alpha,
                    best_score,
                )

                if beta <= alpha:
                    break

            return best_score

        best_score = float("inf")

        for move in moves:
            simulation = game.copy()

            self.apply_move(
                simulation,
                move,
            )

            score = self.minimax(
                simulation,
                depth - 1,
                alpha,
                beta,
                True,
            )

            best_score = min(
                best_score,
                score,
            )

            beta = min(
                beta,
                best_score,
            )

            if beta <= alpha:
                break

        return best_score

    # =========================================================
    # MOVE APPLICATION
    # =========================================================

    def apply_move(self, game, move):
        from_row, from_col, to_row, to_col, promotion = move

        game.move_piece(
            from_row,
            from_col,
            to_row,
            to_col,
            promotion_piece=promotion,
        )

    # =========================================================
    # CAPTURE
    # =========================================================

    def is_capture(self, game, move):
        from_row, from_col, to_row, to_col, _ = move

        piece = game.board[from_row][from_col]
        target = game.board[to_row][to_col]

        if target is not None:
            return target[0] != piece[0]

        # En passant
        if (
            piece[1] == "p"
            and from_col != to_col
            and target is None
        ):
            return True

        return False

    # =========================================================
    # TERMINAL POSITION
    # =========================================================

    def get_terminal_score(self, game, depth):
        color = game.turn

        moves = self.get_all_moves(
            game,
            color,
        )

        if moves:
            return None

        if game.is_in_check(color):
            # Checkmate.
            if color == self.color:
                return -100000 - depth

            return 100000 + depth

        # Stalemate.
        return 0

    # =========================================================
    # EVALUATION
    # =========================================================

    def evaluate(self, game):
        score = 0

        for row in range(8):
            for col in range(8):
                piece = game.board[row][col]

                if piece is None:
                    continue

                color = piece[0]
                piece_type = piece[1]

                value = self.PIECE_VALUES[piece_type]

                positional = self.get_position_value(
                    piece_type,
                    color,
                    row,
                    col,
                )

                total = value + positional

                if color == "w":
                    score += total
                else:
                    score -= total

        # Small bonus for having the move.
        if game.turn == "w":
            score += 5
        else:
            score -= 5

        # Bot's perspective.
        if self.color == "w":
            return score

        return -score

    def get_position_value(
        self,
        piece_type,
        color,
        row,
        col,
    ):
        table = self.TABLES[piece_type]

        if color == "w":
            return table[row][col]

        mirrored_row = 7 - row

        return table[mirrored_row][col]