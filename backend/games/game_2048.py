"""2048 game implementation."""

from __future__ import annotations

import random
from copy import deepcopy
from typing import Any, List, Tuple

from .base import BaseGame

GRID_SIZE = 4


class Game2048(BaseGame):
    """Classic 2048 sliding-tile game."""

    name = "2048"

    def __init__(self) -> None:
        self.board: list[list[int]] = []
        self.score: int = 0
        self.game_over: bool = False
        self.won: bool = False
        self.reset()

    # ── BaseGame interface ──────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        return {
            "game": self.name,
            "board": deepcopy(self.board),
            "score": self.score,
            "game_over": self.game_over,
            "won": self.won,
            "valid_actions": self.valid_actions(),
        }

    def apply_action(self, action: str) -> dict[str, Any]:
        action = action.strip().lower()

        if self.game_over:
            state = self.get_state()
            state["error"] = "Game is already over."
            return state

        if action not in self.valid_actions():
            state = self.get_state()
            state["error"] = f"Invalid action: {action}"
            return state

        moved = self._move(action)
        if moved:
            self._spawn_tile()
            if not self._has_moves():
                self.game_over = True

        return self.get_state()

    def reset(self) -> dict[str, Any]:
        self.board = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.score = 0
        self.game_over = False
        self.won = False
        self._spawn_tile()
        self._spawn_tile()
        return self.get_state()

    def valid_actions(self) -> list[str]:
        if self.game_over:
            return []
        actions = []
        for direction in ("up", "down", "left", "right"):
            if self._can_move(direction):
                actions.append(direction)
        return actions

    # ── Internal helpers ────────────────────────────────────────────

    def _spawn_tile(self) -> None:
        empty = [
            (r, c)
            for r in range(GRID_SIZE)
            for c in range(GRID_SIZE)
            if self.board[r][c] == 0
        ]
        if not empty:
            return
        r, c = random.choice(empty)
        self.board[r][c] = 4 if random.random() < 0.1 else 2

    def _compress(self, row: list[int]) -> tuple[list[int], int, bool]:
        """Slide and merge a single row to the left. Return (new_row, gained_score, changed)."""
        # Remove zeros
        tiles = [v for v in row if v != 0]
        new_row: list[int] = []
        gained = 0
        skip = False

        for i in range(len(tiles)):
            if skip:
                skip = False
                continue
            if i + 1 < len(tiles) and tiles[i] == tiles[i + 1]:
                merged = tiles[i] * 2
                new_row.append(merged)
                gained += merged
                if merged == 2048:
                    self.won = True
                skip = True
            else:
                new_row.append(tiles[i])

        # Pad with zeros
        new_row.extend([0] * (GRID_SIZE - len(new_row)))
        changed = new_row != row
        return new_row, gained, changed

    def _move(self, direction: str) -> bool:
        """Apply a move and return whether the board changed."""
        rotated = self._rotate_to_left(direction)
        any_changed = False
        score_gain = 0

        new_board = []
        for row in rotated:
            new_row, gained, changed = self._compress(row)
            new_board.append(new_row)
            score_gain += gained
            any_changed = any_changed or changed

        if any_changed:
            self.board = self._rotate_from_left(direction, new_board)
            self.score += score_gain
        return any_changed

    def _can_move(self, direction: str) -> bool:
        """Check whether a move in *direction* would change the board."""
        rotated = self._rotate_to_left(direction)
        for row in rotated:
            _, _, changed = self._compress(list(row))
            if changed:
                return True
        return False

    def _has_moves(self) -> bool:
        return any(self._can_move(d) for d in ("up", "down", "left", "right"))

    # ── Board rotation helpers (everything → left, then back) ──────

    def _rotate_to_left(self, direction: str) -> list[list[int]]:
        b = self.board
        if direction == "left":
            return [list(row) for row in b]
        if direction == "right":
            return [list(reversed(row)) for row in b]
        if direction == "up":
            return [list(b[r][c] for r in range(GRID_SIZE)) for c in range(GRID_SIZE)]
        # down
        return [list(b[r][c] for r in reversed(range(GRID_SIZE))) for c in range(GRID_SIZE)]

    def _rotate_from_left(self, direction: str, board: list[list[int]]) -> list[list[int]]:
        if direction == "left":
            return board
        if direction == "right":
            return [list(reversed(row)) for row in board]
        if direction == "up":
            return [
                [board[c][r] for c in range(GRID_SIZE)]
                for r in range(GRID_SIZE)
            ]
        # down
        return [
            [board[c][GRID_SIZE - 1 - r] for c in range(GRID_SIZE)]
            for r in range(GRID_SIZE)
        ]
