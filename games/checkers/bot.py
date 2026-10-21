import random
import time

from .checkers_driver import Checkers


class _Timeout(Exception):
    pass


class CheckersBot:
    MAN_VALUE = 100
    KING_VALUE = 330

    WIN_SCORE = 100000

    # How many extra plies a forced capture chain may add at the search horizon.
    MAX_EXTENSION = 6

    DIFFICULTIES = {
        "Easy": {
            "depth": 0,
            "randomness": 0.35,
            "time": 0.0,
        },
        "Medium": {
            "depth": 3,
            "randomness": 0.10,
            "time": 0.5,
        },
        "Hard": {
            "depth": 5,
            "randomness": 0.03,
            "time": 1.0,
        },
        "Expert": {
            "depth": 8,
            "randomness": 0.00,
            "time": 1.5,
        },
    }

    def __init__(self, color="b", difficulty="Medium"):
        self.color = color

        if difficulty not in self.DIFFICULTIES:
            difficulty = "Medium"

        self.difficulty = difficulty

        settings = self.DIFFICULTIES[difficulty]

        self.depth = settings["depth"]
        self.randomness = settings["randomness"]
        self.time_limit = settings["time"]

        self._deadline = None
        self._nodes = 0

    # =========================================================
    # PUBLIC API
    # =========================================================

    def make_move(self, game):
        """
        Returns a move dict (see Checkers) or None.
        """
        if game.game_over:
            return None

        if game.turn != self.color:
            return None

        moves = game.get_all_legal_moves(self.color)

        if not moves:
            return None

        if len(moves) == 1:
            return moves[0]

        if self.depth == 0:
            return self.choose_easy_move(moves)

        return self.find_best_move(game, moves)

    # =========================================================
    # EASY
    # =========================================================

    def choose_easy_move(self, moves):
        captures = [move for move in moves if move["captures"]]

        # Takes the biggest capture most of the time.
        if captures and random.random() > self.randomness:
            longest = max(len(move["captures"]) for move in captures)

            return random.choice([
                move
                for move in captures
                if len(move["captures"]) == longest
            ])

        return random.choice(moves)

    # =========================================================
    # BEST MOVE (iterative deepening)
    # =========================================================

    def find_best_move(self, game, moves):
        self._deadline = (
            time.monotonic() + self.time_limit
            if self.time_limit > 0
            else None
        )
        self._nodes = 0

        moves = list(moves)
        random.shuffle(moves)

        best_moves = moves

        for depth in range(1, self.depth + 1):
            try:
                scored = self.search_root(game.board, moves, depth)
            except _Timeout:
                break

            best_score = max(score for score, _ in scored)

            best_moves = [
                move
                for score, move in scored
                if score == best_score
            ]

            # Search the best moves first on the next iteration.
            scored.sort(key=lambda pair: -pair[0])
            moves = [move for _, move in scored]

            if abs(best_score) >= self.WIN_SCORE - 100:
                break

        if self.randomness > 0 and random.random() < self.randomness:
            return random.choice(moves)

        return random.choice(best_moves)

    def search_root(self, board, moves, depth):
        opponent = Checkers.opposite_color(self.color)

        scored = []
        best = float("-inf")

        for move in moves:
            new_board = Checkers.copy_board(board)

            Checkers.apply_move_to_board(new_board, move)

            # alpha = best - 1 keeps equal moves exact, so ties can be picked randomly
            alpha = best - 1 if best != float("-inf") else float("-inf")

            score = -self.negamax(
                new_board,
                opponent,
                depth - 1,
                float("-inf"),
                -alpha,
                1,
                0,
            )

            scored.append((score, move))

            best = max(best, score)

        return scored

    # =========================================================
    # NEGAMAX
    # =========================================================

    def negamax(self, board, color, depth, alpha, beta, ply, extension):
        self._nodes += 1

        if (
            self._deadline is not None
            and self._nodes % 256 == 0
            and time.monotonic() > self._deadline
        ):
            raise _Timeout()

        moves = Checkers.generate_moves(board, color)

        if not moves:
            # The side to move has lost; faster wins score higher.
            return -self.WIN_SCORE + ply

        forced = bool(moves[0]["captures"])

        if depth <= 0:
            # Do not stop in the middle of a forced capture exchange.
            if not forced or extension >= self.MAX_EXTENSION:
                return self.evaluate(board, color)

            extension += 1

        moves = self.order_moves(moves)

        opponent = Checkers.opposite_color(color)

        best = float("-inf")

        for move in moves:
            new_board = Checkers.copy_board(board)

            Checkers.apply_move_to_board(new_board, move)

            score = -self.negamax(
                new_board,
                opponent,
                depth - 1,
                -beta,
                -alpha,
                ply + 1,
                extension,
            )

            if score > best:
                best = score

            if best > alpha:
                alpha = best

            if alpha >= beta:
                break

        return best

    @staticmethod
    def order_moves(moves):
        return sorted(
            moves,
            key=lambda move: (
                -len(move["captures"]),
                not move["promotion"],
            ),
        )

    # =========================================================
    # EVALUATION
    # =========================================================

    def evaluate(self, board, color):
        """
        Score from the point of view of `color` (positive = good for `color`).
        """
        score = 0

        for row in range(8):
            for col in range(8):
                piece = board[row][col]

                if piece is None:
                    continue

                if piece[1] == "k":
                    value = self.KING_VALUE

                    # kings like the long diagonal
                    if row + col == 7:
                        value += 10

                else:
                    advance = (7 - row) if piece[0] == "w" else row

                    value = self.MAN_VALUE + advance * 4

                    home_row = 7 if piece[0] == "w" else 0

                    # keeping the back row guards enemy promotion
                    if row == home_row:
                        value += 8

                    if 2 <= row <= 5 and 2 <= col <= 5:
                        value += 3

                if piece[0] == "w":
                    score += value
                else:
                    score -= value

        return score if color == "w" else -score
