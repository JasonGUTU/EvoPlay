"""Four in a Row — human (1) vs. bot (2).

Difficulty levels:
  easy   – rule-based: win if possible, block if needed, else random (center-biased)
  medium – Minimax depth 3
  hard   – Minimax depth 5
"""

from __future__ import annotations

import math
import random
from typing import Any

from .base import BaseGame

ROWS = 6
COLS = 7
EMPTY = 0
HUMAN = 1
BOT = 2
CENTER = COLS // 2

DEPTH_BY_DIFFICULTY = {"easy": 0, "medium": 3, "hard": 5}
VALID_DIFFICULTIES = set(DEPTH_BY_DIFFICULTY)


class FourInARow(BaseGame):
    name = "fourinarow"

    def __init__(self):
        self.difficulty = "hard"
        self._reset_log()
        self.reset()

    def set_difficulty(self, difficulty: str) -> None:
        if difficulty in VALID_DIFFICULTIES:
            self.difficulty = difficulty

    # ── Public interface ──────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        return {
            "game": self.name,
            "board": [row[:] for row in self.board],
            "score": self.score,
            "game_over": self.game_over,
            "won": self.won,
            "winner": self.winner,          # None | "human" | "bot" | "draw"
            "last_bot_col": self.last_bot_col,
            "difficulty": self.difficulty,
            "valid_actions": self.valid_actions(),
        }

    def apply_action(self, action: str) -> dict[str, Any]:
        if self.game_over:
            return self.get_state()

        try:
            col = int(action)
        except ValueError:
            return {**self.get_state(), "error": f"Invalid action: {action}"}

        if col not in range(COLS) or not self._is_valid(col):
            return {**self.get_state(), "error": f"Column {col} is full or out of range"}

        # ── Human move ──────────────────────────────────────────────
        self._drop(col, HUMAN)

        if self._check_win(HUMAN):
            self.game_over = True
            self.won = True
            self.winner = "human"
            self.score = 1
        elif self._is_draw():
            self.game_over = True
            self.winner = "draw"

        state = self.get_state()
        self._record_log(f"human:{col}", state)

        if self.game_over:
            return state

        # ── Bot move (Minimax) ───────────────────────────────────────
        bot_col = self._best_col()
        self.last_bot_col = bot_col
        self._drop(bot_col, BOT)

        if self._check_win(BOT):
            self.game_over = True
            self.winner = "bot"
            self.score = -1
        elif self._is_draw():
            self.game_over = True
            self.winner = "draw"

        state = self.get_state()
        self._record_log(f"bot:{bot_col}", state)
        return state

    def reset(self) -> dict[str, Any]:
        self.board = [[EMPTY] * COLS for _ in range(ROWS)]
        self.game_over = False
        self.won = False
        self.winner = None
        self.score = 0
        self.last_bot_col = None
        self._reset_log()
        return self.get_state()

    # ── Difficulty ────────────────────────────────────────────────────

    def valid_actions(self) -> list[str]:
        if self.game_over:
            return []
        return [str(c) for c in range(COLS) if self._is_valid(c)]

    def get_rules(self) -> str:
        return """Four in a Row (Connect Four) Game Rules

OBJECTIVE:
Drop pieces into a 6-row × 7-column vertical grid. First player to connect 4 of their pieces in a row (horizontally, vertically, or diagonally) wins.

PLAYERS:
- You are player 1 (displayed as "1" on the board). You move first each turn.
- The bot is player 2 (displayed as "2" on the board). It moves automatically after you.

BOARD:
- The board is a 6×7 grid. Row 0 is the top, row 5 is the bottom.
- Empty cells are 0, your pieces are 1, bot pieces are 2.
- Pieces obey gravity: they fall to the lowest empty cell in the chosen column.

AVAILABLE ACTIONS:
- You will be given a list of valid columns. You MUST pick exactly one from that list — do NOT invent your own.
- Choose a column number from 0 to 6 (e.g., "3" to drop in the center column).
- A column is only valid if it is not completely filled (row 0 is not occupied).

GAME OVER CONDITIONS:
- You win if you connect 4 of your pieces in any direction.
- Bot wins if it connects 4 of its pieces.
- Draw if the board is completely filled with no winner.

Respond with ONLY the column number (e.g., "3")."""

    # ── Board helpers ─────────────────────────────────────────────────

    def _is_valid(self, col: int) -> bool:
        return self.board[0][col] == EMPTY

    def _next_row(self, col: int) -> int:
        for r in range(ROWS - 1, -1, -1):
            if self.board[r][col] == EMPTY:
                return r
        return -1

    def _drop(self, col: int, piece: int) -> None:
        r = self._next_row(col)
        if r >= 0:
            self.board[r][col] = piece

    def _is_draw(self) -> bool:
        return all(self.board[0][c] != EMPTY for c in range(COLS))

    def _check_win(self, piece: int) -> bool:
        return _board_wins(self.board, piece)

    # ── Bot move selection ────────────────────────────────────────────

    def _best_col(self) -> int:
        if self.difficulty == "easy":
            return self._easy_col()
        depth = DEPTH_BY_DIFFICULTY[self.difficulty]
        return self._minimax_col(depth)

    def _easy_col(self) -> int:
        """Win immediately if possible; block human win; else random (center-biased)."""
        valid = [c for c in range(COLS) if self._is_valid(c)]
        # Can bot win right now?
        for col in valid:
            r = _drop_inplace(self.board, col, BOT)
            win = _board_wins(self.board, BOT)
            self.board[r][col] = EMPTY
            if win:
                return col
        # Must block human?
        for col in valid:
            r = _drop_inplace(self.board, col, HUMAN)
            win = _board_wins(self.board, HUMAN)
            self.board[r][col] = EMPTY
            if win:
                return col
        # Random with center bias: put center column 3× more likely
        weighted = []
        for col in valid:
            weight = 3 if col == CENTER else 1
            weighted.extend([col] * weight)
        return random.choice(weighted)

    def _minimax_col(self, depth: int) -> int:
        valid = [c for c in range(COLS) if self._is_valid(c)]
        best_score = -math.inf
        best_col = min(valid, key=lambda c: abs(c - CENTER))

        for col in valid:
            r = _drop_inplace(self.board, col, BOT)
            sc = _minimax(self.board, depth - 1, -math.inf, math.inf, False)
            self.board[r][col] = EMPTY
            if sc > best_score:
                best_score = sc
                best_col = col

        return best_col


# ── Pure functions (operate on raw board lists) ───────────────────────

def _drop_inplace(board: list, col: int, piece: int) -> int:
    for r in range(ROWS - 1, -1, -1):
        if board[r][col] == EMPTY:
            board[r][col] = piece
            return r
    return -1


def _board_wins(board: list, piece: int) -> bool:
    # Horizontal
    for r in range(ROWS):
        for c in range(COLS - 3):
            if board[r][c] == piece and board[r][c+1] == piece and \
               board[r][c+2] == piece and board[r][c+3] == piece:
                return True
    # Vertical
    for r in range(ROWS - 3):
        for c in range(COLS):
            if board[r][c] == piece and board[r+1][c] == piece and \
               board[r+2][c] == piece and board[r+3][c] == piece:
                return True
    # Diagonal ↘
    for r in range(ROWS - 3):
        for c in range(COLS - 3):
            if board[r][c] == piece and board[r+1][c+1] == piece and \
               board[r+2][c+2] == piece and board[r+3][c+3] == piece:
                return True
    # Diagonal ↙
    for r in range(3, ROWS):
        for c in range(COLS - 3):
            if board[r][c] == piece and board[r-1][c+1] == piece and \
               board[r-2][c+2] == piece and board[r-3][c+3] == piece:
                return True
    return False


def _score_window(window: list) -> int:
    bot_n = window.count(BOT)
    hum_n = window.count(HUMAN)
    emp_n = window.count(EMPTY)
    if bot_n == 4:
        return 100
    if bot_n == 3 and emp_n == 1:
        return 5
    if bot_n == 2 and emp_n == 2:
        return 2
    if hum_n == 3 and emp_n == 1:
        return -4
    return 0


def _score_board(board: list) -> int:
    score = 0
    # Center column bonus
    score += sum(1 for r in range(ROWS) if board[r][CENTER] == BOT) * 3

    # Horizontal
    for r in range(ROWS):
        for c in range(COLS - 3):
            score += _score_window([board[r][c+i] for i in range(4)])
    # Vertical
    for c in range(COLS):
        for r in range(ROWS - 3):
            score += _score_window([board[r+i][c] for i in range(4)])
    # Diagonal ↘
    for r in range(ROWS - 3):
        for c in range(COLS - 3):
            score += _score_window([board[r+i][c+i] for i in range(4)])
    # Diagonal ↙
    for r in range(3, ROWS):
        for c in range(COLS - 3):
            score += _score_window([board[r-i][c+i] for i in range(4)])
    return score


def _minimax(board: list, depth: int, alpha: float, beta: float, maximizing: bool) -> float:
    if _board_wins(board, BOT):
        return 1_000_000 + depth
    if _board_wins(board, HUMAN):
        return -1_000_000 - depth

    valid = [c for c in range(COLS) if board[0][c] == EMPTY]
    if not valid:
        return 0  # draw
    if depth == 0:
        return _score_board(board)

    if maximizing:
        value = -math.inf
        for col in valid:
            r = _drop_inplace(board, col, BOT)
            value = max(value, _minimax(board, depth - 1, alpha, beta, False))
            board[r][col] = EMPTY
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value
    else:
        value = math.inf
        for col in valid:
            r = _drop_inplace(board, col, HUMAN)
            value = min(value, _minimax(board, depth - 1, alpha, beta, True))
            board[r][col] = EMPTY
            beta = min(beta, value)
            if alpha >= beta:
                break
        return value
