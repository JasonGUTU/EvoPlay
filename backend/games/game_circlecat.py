"""Circle the Cat – hexagonal board game for EvoPlay."""

from __future__ import annotations

import random
from collections import deque
from copy import deepcopy
from typing import Any

from games.base import BaseGame


class CircleCat(BaseGame):
    """
    11x11 hexagonal grid game where the player places walls to trap a cat.
    The cat uses BFS-based smart pathfinding to escape to the boundary.
    Only "hard" difficulty (smart cat).
    """

    name = "circlecat"

    def __init__(self, size: int = 13):
        self.size = size
        self.cat: tuple[int, int] = (size // 2, size // 2)
        self.walls: set[tuple[int, int]] = set()
        self.board: list[list[str]] = []
        self.game_over: bool = False
        self.won: bool = False
        self.score: int = 0
        self.difficulty: str = "hard"
        self._seed: int | None = None
        self._reset_log()
        self._generate()

    # ── Board generation ───────────────────────────────────────────

    def _generate(self, seed: int | None = None):
        if seed is not None:
            self._seed = seed
        elif self._seed is None:
            self._seed = random.randint(0, 2**31)
        rng = random.Random(self._seed)

        center = self.size // 2
        self.board = [["0" for _ in range(self.size)] for _ in range(self.size)]
        self.cat = (center, center)
        self.board[center][center] = "C"
        self.walls = set()

        # Place exactly 10 random walls in the inner 9x9 area
        inner_cells = [
            (i, j)
            for i in range(1, self.size - 1)
            for j in range(1, self.size - 1)
            if (i, j) != self.cat
        ]
        rng.shuffle(inner_cells)
        for i, j in inner_cells[:15]:
            self.board[i][j] = "1"
            self.walls.add((i, j))

        self.game_over = False
        self.won = False
        self.score = 0

    # ── Hex neighbours ─────────────────────────────────────────────

    def get_neighbors(self, pos: tuple[int, int]) -> list[tuple[int, int]]:
        r, c = pos
        if r % 2 == 0:
            offsets = [(-1, 0), (-1, 1), (0, -1), (0, 1), (1, 0), (1, 1)]
        else:
            offsets = [(-1, -1), (-1, 0), (0, -1), (0, 1), (1, -1), (1, 0)]
        result = []
        for dr, dc in offsets:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                result.append((nr, nc))
        return result

    def is_boundary(self, pos: tuple[int, int]) -> bool:
        r, c = pos
        return r == 0 or r == self.size - 1 or c == 0 or c == self.size - 1

    # ── BFS distance to boundary ───────────────────────────────────

    def calculate_distance(self, pos: tuple[int, int], temp_walls: set) -> float:
        visited = {pos}
        q = deque([(pos[0], pos[1], 0)])
        while q:
            x, y, dist = q.popleft()
            if self.is_boundary((x, y)):
                return dist + 1
            for nx, ny in self.get_neighbors((x, y)):
                if (nx, ny) not in visited and (nx, ny) not in temp_walls and (nx, ny) != self.cat:
                    visited.add((nx, ny))
                    q.append((nx, ny, dist + 1))
        return float("inf")

    # ── Smart cat move (hard difficulty) ───────────────────────────

    def find_best_cat_move(self) -> tuple[int, int] | None:
        current_pos = self.cat
        neighbors = self.get_neighbors(current_pos)
        valid_moves = [n for n in neighbors if self.board[n[0]][n[1]] == "0"]

        if not valid_moves:
            return None  # trapped

        # Check for immediate boundary escape
        for move in valid_moves:
            if self.is_boundary(move):
                return move

        # Use simple BFS distance to nearest exit for each move
        best_move = None
        min_dist = float("inf")
        for move in valid_moves:
            dist = self._bfs_to_exit(move)
            if dist < min_dist:
                min_dist = dist
                best_move = move

        return best_move

    def _bfs_to_exit(self, start: tuple[int, int]) -> float:
        """BFS from start to nearest boundary empty cell, ignoring walls."""
        visited = {start, self.cat}
        q = deque([(start, 0)])
        while q:
            pos, dist = q.popleft()
            if self.is_boundary(pos):
                return dist
            for nb in self.get_neighbors(pos):
                if nb not in visited and self.board[nb[0]][nb[1]] != "1":
                    visited.add(nb)
                    q.append((nb, dist + 1))
        return float("inf")

    # ── Display board with E markers ───────────────────────────────

    def _display_board(self) -> list[list[str]]:
        """Return inner 9x9 board (skip outermost ring). Boundary of this visible
        area corresponds to row/col 1 and 9 of the internal 11x11 board."""
        return [row[1:-1] for row in self.board[1:-1]]

    # ── BaseGame interface ─────────────────────────────────────────

    def set_difficulty(self, difficulty: str) -> None:
        """No-op: only hard difficulty is available."""
        self.difficulty = "hard"

    def get_state(self) -> dict[str, Any]:
        # Offset cat_pos and valid_actions to match visible 9x9 coordinates
        vis_cat = [self.cat[0] - 1, self.cat[1] - 1]
        return {
            "board": self._display_board(),
            "game_over": self.game_over,
            "won": self.won,
            "score": self.score,
            "cat_pos": vis_cat,
            "valid_actions": self.valid_actions(),
            "difficulty": self.difficulty,
            "game": self.name,
        }

    def reset(self) -> dict[str, Any]:
        self._seed = random.randint(0, 2**31)
        self._generate(self._seed)
        self._reset_log()
        return self.get_state()

    def apply_action(self, action: str) -> dict[str, Any]:
        if self.game_over:
            return self.get_state()

        # Parse action (visible 9x9 coordinates, convert to internal 11x11)
        try:
            parts = action.strip().split()
            vr, vc = int(parts[0]), int(parts[1])
            r, c = vr + 1, vc + 1  # offset to internal coordinates
        except (ValueError, IndexError):
            state = self.get_state()
            state["error"] = f"Invalid action format: '{action}'. Use 'r c'."
            return state

        # Validate
        if not (1 <= r < self.size - 1 and 1 <= c < self.size - 1):
            state = self.get_state()
            state["error"] = f"Position ({vr},{vc}) is out of bounds."
            return state

        if self.board[r][c] != "0" or self.is_boundary((r, c)):
            state = self.get_state()
            state["error"] = f"Cannot place wall at ({r},{c})."
            return state

        # Place wall
        self.board[r][c] = "1"
        self.walls.add((r, c))

        # Cat's turn
        cat_move = self.find_best_cat_move()

        if cat_move is None:
            # Cat is trapped - player wins
            self.game_over = True
            self.won = True
            self.score = 1
            state = self.get_state()
            self._record_log(action, state)
            return state

        if self.is_boundary(cat_move):
            # Cat reaches exit - player loses
            old_r, old_c = self.cat
            self.board[old_r][old_c] = "0"
            self.board[cat_move[0]][cat_move[1]] = "C"
            self.cat = cat_move
            self.game_over = True
            self.won = False
            self.score = 0
            state = self.get_state()
            self._record_log(action, state)
            return state

        # Cat moves to new position
        old_r, old_c = self.cat
        self.board[old_r][old_c] = "0"
        self.board[cat_move[0]][cat_move[1]] = "C"
        self.cat = cat_move

        # Check if cat is now trapped after moving
        neighbors = self.get_neighbors(cat_move)
        trapped = all(self.board[nr][nc] == "1" for nr, nc in neighbors)
        if trapped:
            self.game_over = True
            self.won = True
            self.score = 1

        state = self.get_state()
        self._record_log(action, state)
        return state

    def valid_actions(self) -> list[str]:
        if self.game_over:
            return []
        actions = []
        # Only interior cells (not outer ring row 0/10, col 0/10)
        # Return visible 9x9 coordinates (offset by -1)
        for i in range(1, self.size - 1):
            for j in range(1, self.size - 1):
                if self.board[i][j] == "0" and not self.is_boundary((i, j)):
                    actions.append(f"{i - 1} {j - 1}")
        return actions

    def get_rules(self) -> str:
        return (
            "Circle the Cat is played on an 11x11 visible hexagonal grid.\n\n"
            "OBJECTIVE: Trap the cat by surrounding it with walls so it cannot reach the boundary.\n\n"
            "RULES:\n"
            "- The cat (C) starts near the center. Some cells start as walls (1).\n"
            "- You and the cat take turns. On your turn, place a wall on any empty interior cell.\n"
            "- The cat then moves one step toward the nearest boundary using smart pathfinding.\n"
            "- The boundary (outermost row/column) is the exit. If the cat reaches it, you lose.\n"
            "- If the cat has no valid moves, you win!\n\n"
            "ACTIONS:\n"
            "- Specify a cell as 'r c' (e.g., '3 5') to place a wall there.\n"
            "- You can only place walls on empty (0) non-boundary cells.\n\n"
            "HEXAGONAL NEIGHBORS:\n"
            "- Even rows: (r-1,c), (r-1,c+1), (r,c-1), (r,c+1), (r+1,c), (r+1,c+1)\n"
            "- Odd rows: (r-1,c-1), (r-1,c), (r,c-1), (r,c+1), (r+1,c-1), (r+1,c)\n"
        )

    def restore_state(self, saved_state: dict[str, Any]) -> None:
        """Restore from saved state."""
        if "board" in saved_state:
            # Convert display board (with E) back to internal board (with 0)
            display_board = saved_state["board"]
            self.board = []
            self.walls = set()
            self.cat = (self.size // 2, self.size // 2)
            for i in range(len(display_board)):
                row = []
                for j in range(len(display_board[i])):
                    cell = display_board[i][j]
                    if cell == "1":
                        row.append("1")
                        self.walls.add((i, j))
                    elif cell == "C":
                        row.append("C")
                        self.cat = (i, j)
                    else:
                        row.append(cell)
                self.board.append(row)
        if "game_over" in saved_state:
            self.game_over = saved_state["game_over"]
        if "won" in saved_state:
            self.won = saved_state["won"]
        if "score" in saved_state:
            self.score = saved_state["score"]
