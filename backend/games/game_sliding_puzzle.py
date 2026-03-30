"""Sliding Puzzle (8-puzzle) — 3×3 number sliding game.

Arrange tiles 1-8 in order by sliding them into the empty space.
Goal state:
  1 2 3
  4 5 6
  7 8 _

Difficulty levels:
  easy   – 10 random shuffles from solved
  medium – 30 random shuffles
  hard   – 80 random shuffles
"""

from __future__ import annotations

import random
from copy import deepcopy
from typing import Any

from .base import BaseGame

SIZE = 3
GOAL = [[1, 2, 3], [4, 5, 6], [7, 8, 0]]

VALID_DIFFICULTIES = {"easy", "medium", "hard"}
HARD_LAYOUTS = [
    [[8, 4, 7], [2, 6, 5], [3, 1, 0]],
    [[1, 8, 4], [2, 6, 7], [0, 3, 5]],
    [[5, 8, 7], [2, 0, 4], [3, 6, 1]],
    [[7, 8, 5], [4, 0, 6], [1, 2, 3]],
    [[3, 2, 7], [6, 5, 4], [0, 8, 1]],
]

# Fixed layouts per difficulty
EASY_LAYOUT = [[1, 2, 3], [5, 0, 6], [4, 7, 8]]

MEDIUM_LAYOUTS = [
    [[1, 7, 4], [8, 2, 0], [3, 6, 5]],
    [[1, 7, 3], [2, 4, 0], [6, 8, 5]],
    [[7, 1, 6], [4, 8, 5], [3, 0, 2]],
    [[7, 6, 3], [1, 8, 4], [0, 5, 2]],
    [[1, 2, 4], [6, 5, 0], [8, 3, 7]],
]

DIRECTIONS = {
    "up":    (-1, 0),
    "down":  (1, 0),
    "left":  (0, -1),
    "right": (0, 1),
}


def _find_blank(board: list) -> tuple[int, int]:
    for r in range(SIZE):
        for c in range(SIZE):
            if board[r][c] == 0:
                return r, c
    return 0, 0


def _is_solved(board: list) -> bool:
    return board == GOAL


class SlidingPuzzle(BaseGame):
    """3×3 sliding number puzzle."""

    name = "sliding_puzzle"

    def __init__(self):
        self.difficulty = "hard"
        self.board: list[list[int]] = []
        self.score = 0
        self.moves = 0
        self.game_over = False
        self.won = False
        self._reset_log()
        self.reset()

    def set_difficulty(self, difficulty: str) -> None:
        if difficulty in VALID_DIFFICULTIES:
            self.difficulty = difficulty

    # ── Public interface ──────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        return {
            "game": self.name,
            "board": deepcopy(self.board),
            "score": self.moves,
            "moves": self.moves,
            "game_over": self.game_over,
            "won": self.won,
            "difficulty": self.difficulty,
            "valid_actions": self.valid_actions(),
        }

    def apply_action(self, action: str) -> dict[str, Any]:
        if self.game_over:
            return self.get_state()

        action = action.strip().lower()

        # Support clicking a tile by position "r c"
        if " " in action:
            try:
                tr, tc = int(action.split()[0]), int(action.split()[1])
            except (ValueError, IndexError):
                return {**self.get_state(), "error": f"Invalid action: '{action}'"}
            br, bc = _find_blank(self.board)
            # Determine direction from tile click
            dr, dc = br - tr, bc - tc
            direction = None
            for d, (ddr, ddc) in DIRECTIONS.items():
                if ddr == dr and ddc == dc:
                    direction = d
                    break
            if direction is None:
                return {**self.get_state(), "error": f"Tile ({tr},{tc}) is not adjacent to blank."}
            action = direction

        if action not in DIRECTIONS:
            return {**self.get_state(), "error": f"Invalid action: '{action}'"}

        dr, dc = DIRECTIONS[action]
        br, bc = _find_blank(self.board)
        # The tile that slides INTO the blank is at (br-dr, bc-dc)
        tr, tc = br - dr, bc - dc

        if not (0 <= tr < SIZE and 0 <= tc < SIZE):
            return {**self.get_state(), "error": f"Cannot move {action}: out of bounds."}

        # Swap blank and tile
        self.board[br][bc] = self.board[tr][tc]
        self.board[tr][tc] = 0
        self.moves += 1

        if _is_solved(self.board):
            self.game_over = True
            self.won = True

        state = self.get_state()
        self._record_log(action, state)
        return state

    def reset(self) -> dict[str, Any]:
        self.moves = 0
        self.game_over = False
        self.won = False
        self._reset_log()
        if self.difficulty == "easy":
            self.board = deepcopy(EASY_LAYOUT)
        elif self.difficulty == "medium":
            self.board = deepcopy(random.choice(MEDIUM_LAYOUTS))
        else:
            self.board = deepcopy(random.choice(HARD_LAYOUTS))
        return self.get_state()

    def valid_actions(self) -> list[str]:
        if self.game_over:
            return []
        br, bc = _find_blank(self.board)
        actions = []
        for d, (dr, dc) in DIRECTIONS.items():
            tr, tc = br - dr, bc - dc
            if 0 <= tr < SIZE and 0 <= tc < SIZE:
                actions.append(d)
        return actions

    def get_rules(self) -> str:
        return """Sliding Puzzle (8-Puzzle) Game Rules

OBJECTIVE:
Arrange the numbered tiles 1-8 in order by sliding them into the empty space. The goal state is:
  1 2 3
  4 5 6
  7 8 _
where _ is the empty space (shown as 0 on the board).

GAMEPLAY:
- The board is a 3×3 grid with tiles numbered 1-8 and one empty space (0).
- Each turn, you slide one tile adjacent to the empty space into it.
- The direction you choose refers to which direction a tile moves INTO the empty space:
  - "up": the tile BELOW the blank slides up
  - "down": the tile ABOVE the blank slides down
  - "left": the tile to the RIGHT of the blank slides left
  - "right": the tile to the LEFT of the blank slides right

AVAILABLE ACTIONS:
- You will be given a list of valid directions. You MUST pick exactly one from that list.
- Directions: "up", "down", "left", "right"
- Not all directions are available every turn (depends on blank position).

GAME OVER CONDITIONS:
- You win when all tiles are in the goal arrangement.
- There is no losing — only the number of moves matters (lower is better).

Respond with ONLY the direction (e.g., "up")."""

    # ── Internal ─────────────────────────────────────────────────────

    def _shuffle(self) -> None:
        """Shuffle by making random valid moves from the solved state."""
        n = SHUFFLE_COUNTS.get(self.difficulty, 30)
        last_dir = None
        opposite = {"up": "down", "down": "up", "left": "right", "right": "left"}
        for _ in range(n):
            br, bc = _find_blank(self.board)
            dirs = []
            for d, (dr, dc) in DIRECTIONS.items():
                tr, tc = br - dr, bc - dc
                if 0 <= tr < SIZE and 0 <= tc < SIZE:
                    # Avoid immediately undoing the last move
                    if last_dir is None or d != opposite[last_dir]:
                        dirs.append(d)
            d = random.choice(dirs)
            dr, dc = DIRECTIONS[d]
            tr, tc = br - dr, bc - dc
            self.board[br][bc] = self.board[tr][tc]
            self.board[tr][tc] = 0
            last_dir = d
        # Ensure not already solved after shuffle
        if _is_solved(self.board):
            self._shuffle()
