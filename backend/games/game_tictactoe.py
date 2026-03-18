"""Tic Tac Toe — human (1, X) vs. bot (2, O).

Difficulty levels:
  easy   – random valid move
  medium – win if possible, block if needed, else random
  hard   – perfect Minimax (3×3 is trivially fast, no pruning needed)
"""

from __future__ import annotations

import math
import random
from typing import Any

from .base import BaseGame

SIZE = 3
EMPTY = 0
HUMAN = 1   # X
BOT = 2     # O

VALID_DIFFICULTIES = {"easy", "medium", "hard"}

LINES = [
    # rows
    [(0,0),(0,1),(0,2)],
    [(1,0),(1,1),(1,2)],
    [(2,0),(2,1),(2,2)],
    # cols
    [(0,0),(1,0),(2,0)],
    [(0,1),(1,1),(2,1)],
    [(0,2),(1,2),(2,2)],
    # diagonals
    [(0,0),(1,1),(2,2)],
    [(0,2),(1,1),(2,0)],
]


# ── Pure board functions ──────────────────────────────────────────────

def _check_win(board: list, piece: int) -> bool:
    return any(all(board[r][c] == piece for r, c in line) for line in LINES)


def _is_full(board: list) -> bool:
    return all(board[r][c] != EMPTY for r in range(SIZE) for c in range(SIZE))


def _valid_cells(board: list) -> list[tuple[int, int]]:
    return [(r, c) for r in range(SIZE) for c in range(SIZE) if board[r][c] == EMPTY]


def _minimax(board: list, maximizing: bool) -> float:
    if _check_win(board, BOT):
        return 1.0
    if _check_win(board, HUMAN):
        return -1.0
    cells = _valid_cells(board)
    if not cells:
        return 0.0

    if maximizing:
        best = -math.inf
        for r, c in cells:
            board[r][c] = BOT
            best = max(best, _minimax(board, False))
            board[r][c] = EMPTY
        return best
    else:
        best = math.inf
        for r, c in cells:
            board[r][c] = HUMAN
            best = min(best, _minimax(board, True))
            board[r][c] = EMPTY
        return best


# ── Game class ────────────────────────────────────────────────────────

class TicTacToe(BaseGame):
    name = "tictactoe"

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
            "winner": self.winner,       # None | "human" | "bot" | "draw"
            "winning_line": self.winning_line,
            "difficulty": self.difficulty,
            "valid_actions": self.valid_actions(),
            "last_bot_move": self.last_bot_move,
        }

    def apply_action(self, action: str) -> dict[str, Any]:
        """Apply human move only; bot move triggered separately via apply_bot_move."""
        if self.game_over:
            return self.get_state()

        try:
            parts = action.strip().split()
            r, c = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            return {**self.get_state(), "error": f"Invalid action: '{action}' — expected 'row col'"}

        if not (0 <= r < SIZE and 0 <= c < SIZE) or self.board[r][c] != EMPTY:
            return {**self.get_state(), "error": f"Cell ({r},{c}) is invalid or occupied"}

        self.board[r][c] = HUMAN
        self._resolve_game_over()
        self._record_log(f"human:{r},{c}", self.get_state())

        state = self.get_state()
        state["bot_pending"] = not self.game_over
        return state

    def apply_bot_move(self) -> dict[str, Any]:
        """Apply bot move and return state with bot_move_pos."""
        if self.game_over:
            return self.get_state()

        bot_pos = self._best_move()
        if bot_pos:
            br, bc = bot_pos
            self.board[br][bc] = BOT
            self.last_bot_move = [br, bc]
            self._resolve_game_over()
            self._record_log(f"bot:{br},{bc}", self.get_state())
            state = self.get_state()
            state["bot_move_pos"] = [br, bc]
            return state

        return self.get_state()

    def reset(self) -> dict[str, Any]:
        self.board = [[EMPTY] * SIZE for _ in range(SIZE)]
        self.game_over = False
        self.won = False
        self.winner = None
        self.score = 0
        self.winning_line = None
        self.last_bot_move = None
        self._reset_log()
        return self.get_state()

    def valid_actions(self) -> list[str]:
        if self.game_over:
            return []
        return [f"{r} {c}" for r, c in _valid_cells(self.board)]

    def get_rules(self) -> str:
        return (
            "Tic Tac Toe 3×3. You are X (1), bot is O (2). "
            "Take turns placing marks; first to get 3 in a row wins. "
            "Action: 'row col' (0-indexed, e.g. '1 1' for center)."
        )

    # ── Helpers ───────────────────────────────────────────────────────

    def _resolve_game_over(self) -> bool:
        for line in LINES:
            cells = [self.board[r][c] for r, c in line]
            if cells[0] != EMPTY and cells[0] == cells[1] == cells[2]:
                self.game_over = True
                piece = cells[0]
                self.winner = "human" if piece == HUMAN else "bot"
                self.won = (piece == HUMAN)
                self.score = 1 if self.won else -1
                self.winning_line = [[r, c] for r, c in line]
                return True
        if _is_full(self.board):
            self.game_over = True
            self.winner = "draw"
            return True
        return False

    def _best_move(self) -> tuple[int, int] | None:
        cells = _valid_cells(self.board)
        if not cells:
            return None

        if self.difficulty == "easy":
            return random.choice(cells)

        if self.difficulty == "medium":
            # Win immediately if possible
            for r, c in cells:
                self.board[r][c] = BOT
                win = _check_win(self.board, BOT)
                self.board[r][c] = EMPTY
                if win:
                    return (r, c)
            # Block human win
            for r, c in cells:
                self.board[r][c] = HUMAN
                win = _check_win(self.board, HUMAN)
                self.board[r][c] = EMPTY
                if win:
                    return (r, c)
            return random.choice(cells)

        # Hard: full minimax
        best_score = -math.inf
        best = cells[0]
        for r, c in cells:
            self.board[r][c] = BOT
            sc = _minimax(self.board, False)
            self.board[r][c] = EMPTY
            if sc > best_score:
                best_score = sc
                best = (r, c)
        return best
