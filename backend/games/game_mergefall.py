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

VALID_DIFFICULTIES = {"easy", "medium", "hard"}

# Difficulty controls tile sampling spread (higher = more random/harder)
# temp_base: base temperature for distribution, small_penalty: weight for tiles <=8
DIFF_PARAMS = {
    "easy":   {"temp_base": 1.0,  "temp_high": 0.85, "small_pen": 0.55, "high_pen": 0.12, "max_pen": 0.02, "min_max": 0},
    "medium": {"temp_base": 2.5,  "temp_high": 2.0,  "small_pen": 0.90, "high_pen": 0.40, "max_pen": 0.15, "min_max": 0},
    "hard":   {"temp_base": 2.5,  "temp_high": 2.0,  "small_pen": 0.90, "high_pen": 0.40, "max_pen": 0.15, "min_max": 64},
}


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
        self.difficulty: str = "hard"
        self._active_pos: Tuple[int, int] | None = None
        self._last_tile: int = 0  # Track last spawned tile for anti-repeat
        self._reset_log()
        self.reset()

    def set_difficulty(self, difficulty: str) -> None:
        if difficulty in VALID_DIFFICULTIES:
            self.difficulty = difficulty

    # ── BaseGame interface ──────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        # Only expose the visible rows (skip the overflow row 0)
        visible_board = [
            [abs(v) for v in self.board[r]]
            for r in range(1, self.height)
        ]
        state = {
            "game": self.name,
            "board": deepcopy(visible_board),
            "width": self.width,
            "height": self.visible_height,
            "score": self.score,
            "next_tile": self.next_tile,
            "difficulty": self.difficulty,
        }
        va = self.valid_actions()
        # If no valid actions remain, force game over
        if not self.game_over and not va:
            self.game_over = True
        state.update({
            "game_over": self.game_over,
            "valid_actions": va if not self.game_over else [],
        })
        if self._pre_merge_board is not None:
            state["pre_merge_board"] = self._pre_merge_board
            state["drop_pos"] = self._drop_pos
        return state

    def reset(self) -> dict[str, Any]:
        self.board = [[0] * self.width for _ in range(self.height)]
        self.score = 0
        self.game_over = False
        self._active_pos = None
        self._pre_merge_board = None
        self._drop_pos = None
        self._reset_log()
        self.next_tile = self._sample_next_tile()
        return self.get_state()

    def valid_actions(self) -> list[str]:
        if self.game_over:
            return []
        actions = []
        for c in range(self.width):
            if self.board[1][c] == 0:
                # Column not full
                actions.append("drop %d" % c)
            else:
                # Column full — only valid if next_tile can merge with the top tile
                if self.board[1][c] == self.next_tile:
                    actions.append("drop %d" % c)
        return actions
    
    def get_rules(self) -> str:
        """Return the game rules description."""
        return """MergeFall Game Rules

OBJECTIVE:
Drop numbered tiles into columns to create chains of merges and combos. Your goal is to achieve the highest score possible by strategically placing tiles and triggering cascading merges.

GAMEPLAY:
- You have a 5x6 grid (5 columns, 6 visible rows).
- Each turn, you choose a column (0-4) to drop the next tile into.
- The tile falls down the column and lands on top of existing tiles or at the bottom.
- After dropping, the game automatically resolves merges and gravity:
  1. Gravity: All tiles fall down to fill empty spaces.
  2. Merging: If the dropped tile has any adjacent tiles (up/down/left/right) with the same value, it absorbs all such neighbors in its immediate 4-neighborhood.
  3. The merged tile's value upgrades based on how many tiles were absorbed.
  4. After merging, gravity applies again, and the process repeats until no more merges are possible.
- Your score increases based on the final merged tile value multiplied by the combo count.

AVAILABLE ACTIONS:
You can drop a tile into any of the 5 columns using the format "drop <column_number>":
- "drop 0": Drop into the leftmost column (column 0)
- "drop 1": Drop into the second column (column 1)
- "drop 2": Drop into the middle column (column 2)
- "drop 3": Drop into the fourth column (column 3)
- "drop 4": Drop into the rightmost column (column 4)

You can also use just the number: "0", "1", "2", "3", or "4" as shorthand.

GAME OVER CONDITIONS:
The game ends when:
- After dropping a tile and resolving all merges, any tile remains in the overflow row (above the visible 6 rows).
- This happens when a column becomes completely full and cannot accommodate the dropped tile.

Note: Even if a column looks full, dropping into it might trigger merges that clear space. However, if the column is truly full (including the overflow row), the game ends immediately."""

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
            state = self.get_state()
            state["error"] = "Column %d is full! Choose another column." % col
            return state

        # If visible top row is occupied, check if dropping would trigger a merge
        if self.board[1][col] != 0:
            if not self._would_merge_on_drop(col, self.next_tile):
                state = self.get_state()
                state["error"] = "Column %d is full and no merge possible. Choose another column." % col
                return state

        # Drop the tile (may land in overflow row 0, that's OK for now)
        r = self._drop_active_into_column(col, self.next_tile)
        self._active_pos = (r, col)

        # Capture pre-merge board (after drop, before merge) for animation
        # Finalize active marker so it shows as a positive number
        self._pre_merge_board = [
            [abs(v) for v in self.board[row]]
            for row in range(1, self.height)
        ]
        self._drop_pos = [r - 1, col] if r > 0 else [0, col]  # visible row index

        # Resolve all merges and gravity
        gained = self._resolve_active_drop()
        self.score += gained

        # NOW check overflow: if any tile remains in row 0, game over
        if any(self.board[0][c] != 0 for c in range(self.width)):
            self.game_over = True

        # Generate next tile before checking game over (valid_actions depends on next_tile)
        if not self.game_over:
            self.next_tile = self._sample_next_tile()

        # Game over if no valid actions remain (all columns full, no possible merges with new tile)
        if not self.game_over and not self.valid_actions():
            self.game_over = True

        state = self.get_state()
        self._record_log(action, state)
        # Clear pre_merge after it's been read once via get_state
        self._pre_merge_board = None
        self._drop_pos = None
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
        """Resolve gravity + absorption chains. Return score gained.

        Logic:
        1. Active tile absorbs direct same-value neighbors
        2. Gravity applies — tiles fall down
        3. Any tile that MOVED during gravity and has same-value neighbors
           becomes the new active tile and absorbs them
        4. Repeat until stable
        """
        if self._active_pos is None:
            return 0

        total_score = 0
        while True:
            # Only let the active tile fall (not all tiles)
            self._settle_active_tile()
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
            total_score += new_v

        # Finalize active marker
        self._finalize_active()

        # Now apply full gravity and handle cascades from fallen tiles
        total_score += self._resolve_gravity_cascades()
        return total_score

    def _settle_active_tile(self) -> None:
        """Let only the active tile fall down to the lowest empty cell in its column."""
        if self._active_pos is None:
            return
        ar, ac = self._active_pos
        v = self.board[ar][ac]
        if v == 0:
            self._active_pos = None
            return
        # Find lowest empty cell below active in the same column
        lowest = ar
        for r in range(ar + 1, self.height):
            if self.board[r][ac] == 0:
                lowest = r
            else:
                break
        if lowest != ar:
            self.board[ar][ac] = 0
            self.board[lowest][ac] = v
            self._active_pos = (lowest, ac)

    def _resolve_gravity_cascades(self) -> int:
        """After active chain ends, apply gravity and check for merges.
        First check fallen tiles, then scan all tiles for adjacent same-value pairs.
        Repeat until stable."""
        total_score = 0
        while True:
            before = [row[:] for row in self.board]
            self._apply_gravity()

            # Priority 1: check tiles that fell during gravity
            merged_any = False
            for c in range(self.width):
                for r in range(self.height - 1, -1, -1):
                    v = abs(self.board[r][c])
                    if v != 0 and before[r][c] == 0:
                        neighbors = self._same_value_neighbors(r, c, v)
                        if neighbors:
                            for nr, nc in neighbors:
                                self.board[nr][nc] = 0
                            n = 1 + len(neighbors)
                            new_v = v * (1 << self._ceil_log2(n))
                            self.board[r][c] = new_v
                            total_score += new_v
                            merged_any = True
                            break
                if merged_any:
                    break

            if merged_any:
                continue

            # Priority 2: scan entire board for any adjacent same-value pair
            for r in range(self.height - 1, -1, -1):
                for c in range(self.width):
                    v = self.board[r][c]
                    if v == 0:
                        continue
                    neighbors = self._same_value_neighbors(r, c, v)
                    if neighbors:
                        for nr, nc in neighbors:
                            self.board[nr][nc] = 0
                        n = 1 + len(neighbors)
                        new_v = v * (1 << self._ceil_log2(n))
                        self.board[r][c] = new_v
                        total_score += new_v
                        merged_any = True
                        break
                if merged_any:
                    break

            if not merged_any:
                break
        return total_score

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

    def _would_merge_on_drop(self, col: int, tile_value: int) -> bool:
        """Check if dropping tile_value into col would trigger a merge (without modifying board)."""
        # Find where the tile would land
        land_row = None
        for r in range(self.height - 1, -1, -1):
            if self.board[r][col] == 0:
                land_row = r
                break
        if land_row is None:
            return False
        # Check if any neighbor at that position has the same value
        for nr, nc in ((land_row - 1, col), (land_row + 1, col), (land_row, col - 1), (land_row, col + 1)):
            if 0 <= nr < self.height and 0 <= nc < self.width:
                if abs(self.board[nr][nc]) == tile_value:
                    return True
        return False

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
        dp = DIFF_PARAMS.get(self.difficulty, DIFF_PARAMS["easy"])

        # Hard mode: treat M as at least min_max so large tiles can appear from the start
        min_max = dp.get("min_max", 0)
        if min_max > 0:
            M = max(M, min_max)

        if M < 2:
            return 2

        # Cap the max spawnable tile at 128
        M = min(M, 128)

        max_exp = int(math.log2(M))
        candidates = [1 << e for e in range(1, max_exp + 1)]

        center_val = self._floor_pow2(max(4, M // 32))
        center_exp = int(math.log2(center_val))
        temp = dp["temp_high"] if M >= 128 else dp["temp_base"]

        weights: list[float] = []
        for v in candidates:
            e = int(math.log2(v))
            dist = abs(e - center_exp)
            w = math.exp(-dist / temp)
            if v <= 8:
                w *= dp["small_pen"]
            if M >= 64 and v == M // 2:
                w *= dp["high_pen"]
            if M >= 64 and v == M:
                w *= dp["max_pen"]
            # Hard mode: penalize repeating the same tile as last turn
            if self.difficulty == "hard" and v == self._last_tile:
                w *= 0.15
            weights.append(w)

        s = sum(weights)
        if s <= 0:
            return 2
        x = self.rng.random() * s
        cum = 0.0
        for v, w in zip(candidates, weights):
            cum += w
            if x <= cum:
                self._last_tile = v
                return v
        return candidates[-1]

    # ── Math helper ─────────────────────────────────────────────────

    @staticmethod
    def _ceil_log2(n: int) -> int:
        if n <= 1:
            return 0
        return (n - 1).bit_length()
