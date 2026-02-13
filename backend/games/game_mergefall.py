"""MergeFall – A Merge & Drop Puzzle Game implementation.

Rules:
- Grid: width=5, height=6.
- Each turn: player chooses a column via action string "drop <col>" (e.g., "drop 0").
- A tile (next_tile) drops into that column and stacks on existing tiles.
- Resolve:
    1) Apply gravity (everything falls down).
    2) If the active tile has ANY same-valued orthogonal neighbor (up/down/left/right),
       it absorbs ALL such neighbors in that immediate 4-neighborhood (no recursion).
       The active tile value upgrades to v * 2**ceil(log2(n)), where n = 1 + absorbed_count.
       This counts as one combo step.
    3) After absorption, empty cells may cause other tiles to fall (gravity), and the active tile
       may become adjacent to same-valued neighbors again, repeating step (2).
    4) Stop when no absorption is possible.
- Game Over: after drop+merge resolves, if any tile still pokes above the visible
  6-row area (overflow row), the game ends. Merging can save you even on a full column.
- Scoring for the turn: (final_active_value) * combo. If combo=0, gain is 0.
- next_tile distribution is dynamic based on current maximum tile on board.
"""

from __future__ import annotations

import math
import random
from copy import deepcopy
from typing import Any, List, Tuple

from .base import BaseGame

DEFAULT_WIDTH = 5
DEFAULT_HEIGHT = 6


class MergeFall(BaseGame):
    """MergeFall – drop numbers, merge neighbors, chain combos."""

    name = "mergefall"

    def __init__(
        self,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        seed: int | None = None,
    ) -> None:
        self.width = int(width)
        self.visible_height = int(height)      # rows the player sees (6)
        self.height = self.visible_height + 1   # +1 overflow row at the top
        self.rng = random.Random(seed)
        self.board: list[list[int]] = []
        self.score: int = 0
        self.game_over: bool = False
        self.next_tile: int = 2
        self._active_pos: Tuple[int, int] | None = None
        self._reset_log()
        self.reset()

    # ── BaseGame interface ──────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        # Only expose the visible rows (skip the overflow row 0)
        visible_board = [
            [abs(v) for v in self.board[r]]
            for r in range(1, self.height)
        ]
        return {
            "game": self.name,
            "board": deepcopy(visible_board),
            "width": self.width,
            "height": self.visible_height,
            "score": self.score,
            "next_tile": self.next_tile,
            "game_over": self.game_over,
            "valid_actions": self.valid_actions(),
        }

    def reset(self) -> dict[str, Any]:
        self.board = [[0] * self.width for _ in range(self.height)]
        self.score = 0
        self.game_over = False
        self._active_pos = None
        self._reset_log()
        self.next_tile = self._sample_next_tile()
        return self.get_state()

    def valid_actions(self) -> list[str]:
        if self.game_over:
            return []
        # All columns are always valid — dropping into a full column = overflow = game over.
        return ["drop %d" % c for c in range(self.width)]

    def apply_action(self, action: str) -> dict[str, Any]:
        action = action.strip().lower()

        if self.game_over:
            state = self.get_state()
            state["error"] = "Game is already over."
            return state

        col = self._parse_action_to_col(action)
        if col is None or not (0 <= col < self.width):
            state = self.get_state()
            state["error"] = "Invalid action: %s" % action
            return state

        # Check if column is completely full (no empty cell even in overflow row)
        if self.board[0][col] != 0:
            # Truly no room at all — cannot even place the tile
            self.game_over = True
            state = self.get_state()
            state["error"] = "Column %d has no room. Game over." % col
            return state

        # Drop the tile (may land in overflow row 0, that's OK for now)
        r = self._drop_active_into_column(col, self.next_tile)
        self._active_pos = (r, col)

        # Resolve all merges and gravity
        gained = self._resolve_active_drop()
        self.score += gained

        # NOW check overflow: if any tile remains in row 0, game over
        if any(self.board[0][c] != 0 for c in range(self.width)):
            self.game_over = True

        if not self.game_over:
            self.next_tile = self._sample_next_tile()

        state = self.get_state()
        self._record_log(action, state)
        return state

    # ── Action parsing ──────────────────────────────────────────────

    def _parse_action_to_col(self, action: str) -> int | None:
        if action.isdigit():
            return int(action)
        if action.startswith("drop"):
            tail = action[4:].strip()
            if not tail:
                return None
            for sep in (" ", ":", "=", "\t"):
                if sep in tail:
                    parts = [p for p in tail.split(sep) if p]
                    if parts and parts[0].isdigit():
                        return int(parts[0])
            if tail.isdigit():
                return int(tail)
        return None

    # ── Core mechanics ──────────────────────────────────────────────

    def _drop_active_into_column(self, col: int, value: int) -> int:
        for r in range(self.height - 1, -1, -1):
            if self.board[r][col] == 0:
                self.board[r][col] = -value  # negative = active marker
                return r
        raise RuntimeError("Column should not be full.")

    def _resolve_active_drop(self) -> int:
        """Resolve gravity + absorption chains. Return score gained."""
        if self._active_pos is None:
            return 0

        combo = 0
        while True:
            self._apply_gravity()
            if self._active_pos is None:
                break

            ar, ac = self._active_pos
            v = abs(self.board[ar][ac])
            if v == 0:
                break

            neighbors = self._same_value_neighbors(ar, ac, v)
            if not neighbors:
                break

            for nr, nc in neighbors:
                self.board[nr][nc] = 0

            n = 1 + len(neighbors)
            new_v = v * (1 << self._ceil_log2(n))
            self.board[ar][ac] = -new_v
            combo += 1

        final_value = self._finalize_active_and_get_value()
        return 0 if combo == 0 else final_value * combo

    def _same_value_neighbors(
        self, r: int, c: int, target: int
    ) -> List[Tuple[int, int]]:
        out: List[Tuple[int, int]] = []
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < self.height and 0 <= nc < self.width:
                if abs(self.board[nr][nc]) == target:
                    out.append((nr, nc))
        return out

    def _apply_gravity(self) -> None:
        new_active_pos = None
        for c in range(self.width):
            col_vals = [
                self.board[r][c]
                for r in range(self.height)
                if self.board[r][c] != 0
            ]
            new_col = [0] * self.height
            rr = self.height - 1
            for val in reversed(col_vals):
                new_col[rr] = val
                if val < 0:
                    new_active_pos = (rr, c)
                rr -= 1
            for r in range(self.height):
                self.board[r][c] = new_col[r]
        self._active_pos = new_active_pos

    def _finalize_active(self) -> None:
        if self._active_pos is None:
            return
        r, c = self._active_pos
        self.board[r][c] = abs(self.board[r][c])
        self._active_pos = None

    def _finalize_active_and_get_value(self) -> int:
        if self._active_pos is None:
            return 0
        r, c = self._active_pos
        val = abs(self.board[r][c])
        self.board[r][c] = val
        self._active_pos = None
        return val

    # ── next_tile sampling ──────────────────────────────────────────

    def _current_max_tile(self) -> int:
        m = 2
        for r in range(self.height):
            for c in range(self.width):
                m = max(m, abs(self.board[r][c]))
        return m

    @staticmethod
    def _floor_pow2(x: int) -> int:
        return 1 << (x.bit_length() - 1)

    def _sample_next_tile(self) -> int:
        M = self._current_max_tile()
        if M < 2:
            return 2

        max_exp = int(math.log2(M))
        candidates = [1 << e for e in range(1, max_exp + 1)]

        center_val = self._floor_pow2(max(4, M // 32))
        center_exp = int(math.log2(center_val))
        temp = 0.85 if M >= 128 else 1.0

        weights: list[float] = []
        for v in candidates:
            e = int(math.log2(v))
            dist = abs(e - center_exp)
            w = math.exp(-dist / temp)
            if v <= 8:
                w *= 0.55
            if M >= 64 and v == M // 2:
                w *= 0.12
            if M >= 64 and v == M:
                w *= 0.02
            weights.append(w)

        s = sum(weights)
        if s <= 0:
            return 2
        x = self.rng.random() * s
        cum = 0.0
        for v, w in zip(candidates, weights):
            cum += w
            if x <= cum:
                return v
        return candidates[-1]

    # ── Math helper ─────────────────────────────────────────────────

    @staticmethod
    def _ceil_log2(n: int) -> int:
        if n <= 1:
            return 0
        return (n - 1).bit_length()
