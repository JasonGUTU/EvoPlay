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
        self._reset_log()
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

        state = self.get_state()
        self._record_log(action, state)
        return state

    def reset(self) -> dict[str, Any]:
        self.board = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.score = 0
        self.game_over = False
        self.won = False
        self._reset_log()
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
    
    def get_rules(self) -> str:
        """Return the game rules description."""
        return """2048 Game Rules

OBJECTIVE:
The goal is to slide numbered tiles on a 4x4 grid to combine them and create a tile with the number 2048. You win when you reach 2048, but you can continue playing to achieve higher scores.

GAMEPLAY:
- You start with a 4x4 grid containing two tiles (either 2 or 4).
- On each turn, you slide all tiles in one of four directions: up, down, left, or right.
- When you slide, all tiles move as far as possible in that direction until they hit the edge or another tile.
- If two tiles with the same number collide while moving, they merge into a single tile with double the value.
- After each move, a new tile (either 2 with 90% probability or 4 with 10% probability) appears in a random empty cell.

AVAILABLE ACTIONS:
You can choose one of four directions:
- "up": Slide all tiles upward
- "down": Slide all tiles downward
- "left": Slide all tiles to the left
- "right": Slide all tiles to the right

Note: Only actions that would actually change the board state are valid. If a direction would not move any tiles, that action is not available.

GAME OVER CONDITIONS:
The game ends when:
1. The board is completely filled with tiles, AND
2. No valid moves are possible (no tiles can merge in any direction)

When the game is over, you cannot make any more moves. Your final score is the sum of all merged tile values."""

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
