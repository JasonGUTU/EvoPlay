"""Nuts and Bolts game implementation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .base import BaseGame

# 3 full screws + 2 empty = 5 screws
NUM_SCREWS = 5
SCREW_CAPACITY = 3
MAX_UNDOS = 2

class NutsBolts(BaseGame):
    """Nuts and bolts sorting game."""

    name = "nuts_bolts"

    def __init__(self) -> None:
        self.screws: list[list[str]] = []
        self.score: int = 0
        self.game_over: bool = False
        self.won: bool = False
        self.undos_remaining: int = MAX_UNDOS
        self.history: list[dict[str, Any]] = []
        self.selected_screw: int | None = None
        self.current_level: int = 1
        self.max_level: int = 10
        self.screw_capacity: int = 3
        self.num_screws: int = NUM_SCREWS
        self._reset_log()
        self.reset()

    # ── BaseGame interface ──────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        return {
            "game": self.name,
            "board": deepcopy(self.screws),
            "score": self.score,
            "game_over": self.game_over,
            "won": self.won,
            "valid_actions": self.valid_actions(),
            "undos_remaining": self.undos_remaining,
            "selected_screw": self.selected_screw,
            "current_level": self.current_level,
            "max_level": self.max_level,
            "screw_capacity": self.screw_capacity,
            "num_screws": self.num_screws
        }

    def apply_action(self, action: str) -> dict[str, Any]:
        action = action.strip().lower()

        if self.game_over and action != "next_level":
            state = self.get_state()
            state["error"] = "Game is already over."
            return state

        if action not in self.valid_actions():
            state = self.get_state()
            state["error"] = f"Invalid action: {action}"
            return state

        if action == "undo":
            self._apply_undo()
        elif action == "next_level":
            self.current_level += 1
            self._load_level(self.current_level)
        elif action.startswith("move_"):
            # New format: "move_A_B"
            parts = action.split("_")
            if len(parts) == 3:
                src_idx = int(parts[1])
                dst_idx = int(parts[2])
                
                moved = self._move_continuous(src_idx, dst_idx)
                if moved:
                    self._check_win_condition()
                    if self.won:
                        self.game_over = True
                else:
                    state = self.get_state()
                    state["error"] = "Invalid move."
                    return state
        elif action.startswith("select_"):
            # Keep select_ for backward compatibility if needed, but it's deprecated
            pass
        
        state = self.get_state()
        self._record_log(action, state)
        return state

    def reset(self) -> dict[str, Any]:
        self._reset_log()
        self._load_level(self.current_level)
        return self.get_state()
        
    def _load_level(self, level: int) -> None:
        """Load the given level's configuration."""
        self.score = 0
        self.game_over = False
        self.won = False
        self.undos_remaining = MAX_UNDOS
        self.history = []
        self.selected_screw = None
        
        if level == 1:
            # New Level 1 from image: 4 screws, capacity 5
            # Two screws with mixed nuts, two empty
            self.screw_capacity = 5
            self.num_screws = 4
            self.screws = [
                ['r', 'r', 'r', 'y', 'y'], # Left screw: 3 red, 2 yellow (bottom to top)
                ['y', 'y', 'y', 'r', 'r'], # Right screw: 3 yellow, 2 red (bottom to top)
                [],
                []
            ]
        elif level == 2:
            # Previous Level 1
            self.screw_capacity = 3
            self.num_screws = 5
            self.screws = [
                ['r', 'r', 'b'],
                ['r', 'y', 'y'],
                ['y', 'b', 'b'],
                [],
                []
            ]
        elif level == 3:
            # Previous Level 2
            self.screw_capacity = 4
            self.num_screws = 6
            self.screws = [
                ['b', 'b', 'b', 'r'],
                ['r', 'g', 'g', 'g'],
                ['r', 'r', 'b', 'y'],
                ['y', 'y', 'y', 'g'],
                [],
                []
            ]
        elif level == 4:
            # New Level 4: 8 screws (6 filled, 2 empty), capacity 3
            # Colors: Pink(p), Orange(o), Red(r), Green(g), Blue(b), Yellow(y)
            self.screw_capacity = 3
            self.num_screws = 8
            self.screws = [
                ['p', 'o', 'o'], # 1: Pink, Orange, Orange
                ['o', 'r', 'r'], # 2: Orange, Red, Red
                ['g', 'g', 'p'], # 3: Green, Green, Pink
                ['b', 'y', 'y'], # 4: Blue, Yellow, Yellow
                ['r', 'b', 'b'], # 5: Red, Blue, Blue
                ['y', 'p', 'g'], # 6: Yellow, Pink, Green
                [],
                []
            ]
        elif level == 5:
            # New Level 5: 9 screws (7 filled, 2 empty), capacity 3
            # Top 5, Bottom 4.
            # Colors: r, y, b(dark), g, o, p, c(cyan/light blue)
            self.screw_capacity = 3
            self.num_screws = 9
            self.screws = [
                # Top Row (5 screws)
                ['c', 'y', 'r'], # 1: Blue, Yellow, Red
                ['o', 'g', 'c'], # 2: Orange, Green, Cyan
                ['o', 'r', 'p'], # 3: Orange, Red, Pink
                ['o', 'y', 'p'], # 4: Orange, Yellow, Pink
                ['b', 'b', 'g'], # 5: Blue, Blue, Green
                # Bottom Row (4 screws: 2 filled, 2 empty)
                ['b', 'r', 'c'], # 6: Blue, Red, Cyan
                ['y', 'p', 'g'], # 7: Yellow, Pink, Green
                [],              # 8: Empty
                []               # 9: Empty
            ]
        elif level == 6:
            # New Level 6: 16 screws (14 filled, 2 empty), capacity 3
            # Top 5, Mid 6, Bot 5.
            # Colors: 
            #   Greens: g (grass/light green), t (teal), k (dark green)
            #   Purples: v (violet/deep), m (magenta/pinkish)
            self.screw_capacity = 3
            self.num_screws = 16
            self.screws = [
                # Top Row (5 screws)
                ['d', 'c', 's'], # 1: Sand, Cyan, Silver
                ['d', 'o', 'r'], # 2: Sand, Orange, Red
                ['v', 'y', 's'], # 3: Violet, Yellow, Silver
                ['k', 'v', 's'], # 4: Dark Green, Violet, Silver
                ['m', 'g', 'k'], # 5: Magenta, Grass Green, Dark Green
                # Middle Row (6 screws)
                ['g', 'r', 'p'], # 6: Grass Green, Red, Pink
                ['c', 'k', 'n'], # 7: Cyan, Dark Green, Brown
                ['c', 'm', 'm'], # 8: Cyan, Magenta, Magenta
                ['g', 'p', 'd'], # 9: Grass Green, Pink, Sand
                ['t', 'p', 'n'], # 10: Teal, Pink, Brown
                ['t', 'o', 'n'], # 11: Teal, Orange, Brown
                # Bottom Row (5 screws: 3 filled, 2 empty)
                ['b', 't', 'v'], # 12: Blue, Teal, Violet
                ['r', 'b', 'o'], # 13: Red, Blue, Orange
                ['y', 'y', 'b'], # 14: Yellow, Yellow, Blue
                [],              # 15: Empty
                []               # 16: Empty
            ]
        elif level == 7:
            # New Level 7: 14 screws (12 filled, 2 empty), capacity 4
            # Colors: 12 distinct colors (all from L6 + Lime 'l')
            # Layout: Top 5, Mid 5, Bot 4
            self.screw_capacity = 4
            self.num_screws = 14
            self.screws = [
                # Top Row (5 screws)
                ['s', 'l', 'y', 'l'], # 1: Silver, Lime, Yellow, Lime
                ['t', 't', 'p', 'p'], # 2: Teal, Teal, Pink, Pink
                ['t', 'g', 'v', 's'], # 3: Teal, Green, Violet, Silver
                ['v', 's', 'r', 'b'], # 4: Violet, Silver, Red, Blue
                ['v', 'r', 'b', 'r'], # 5: Violet, Red, Blue, Red
                # Middle Row (5 screws)
                ['g', 'r', 'o', 'o'], # 6: Green, Red, Orange, Orange
                ['n', 'n', 'b', 'g'], # 7: Brown, Brown, Blue, Green
                ['n', 'o', 't', 'c'], # 8: Brown, Orange, Teal, Cyan
                ['c', 'p', 's', 'v'], # 9: Cyan, Pink, Silver, Violet
                ['p', 'c', 'c', 'l'], # 10: Pink, Cyan, Cyan, Lime
                # Bottom Row (4 screws)
                ['o', 'g', 'b', 'l'], # 11: Orange, Green, Blue, Lime
                ['y', 'y', 'n', 'y'], # 12: Yellow, Yellow, Brown, Yellow
                [],                   # 13: Empty
                []                    # 14: Empty
            ]
        elif level == 8:
            # New Level 8: 11 screws (9 filled, 2 empty), capacity 6
            # Colors: 9 distinct colors (Red, Orange, Yellow, Green, Blue, Cyan, Pink, Violet, Brown)
            # Layout: Top 6, Bot 5
            self.screw_capacity = 6
            self.num_screws = 11
            self.screws = [
                # Top Row (6 screws)
                ['p', 'n', 'n', 'o', 'b', 'g'], # 1: Pink, Brown, Brown, Orange, Blue, Green
                ['r', 'o', 'y', 'g', 'y', 'b'], # 2: Red, Orange, Yellow, Green, Yellow, Blue
                ['r', 'c', 'g', 'c', 'p', 'b'], # 3: Red, Cyan, Green, Cyan, Pink, Blue
                ['c', 'n', 'p', 'p', 'y', 'o'], # 4: Cyan, Brown, Pink, Pink, Yellow, Orange
                ['g', 'b', 'y', 'c', 'b', 'r'], # 5: Green, Blue, Yellow, Cyan, Blue, Red
                ['y', 'o', 'p', 'g', 'n', 'c'], # 6: Yellow, Orange, Pink, Green, Brown, Cyan
                # Bottom Row (5 screws: 3 filled, 2 empty)
                ['r', 'y', 'b', 'g', 'o', 'p'], # 7: Mixed
                ['c', 'v', 'n', 'r', 'y', 'b'], # 8: Mixed
                ['g', 'o', 'p', 'c', 'v', 'n'], # 9: Mixed
                [],                             # 10: Empty
                []                              # 11: Empty
            ]
        elif level == 9:
            # Previous Level 8 (now 9): 16 screws (14 filled, 2 empty), capacity 4
            # Colors: 14 distinct colors
            # Layout: Top 5, Mid 6, Bot 5
            self.screw_capacity = 4
            self.num_screws = 16
            self.screws = [
                # Top Row (5 screws)
                ['d', 'b', 't', 't'], # 1: Sand, Blue, Teal, Teal
                ['v', 'b', 'l', 'p'], # 2: Violet, Blue, Lime, Pink
                ['s', 'y', 'v', 'v'], # 3: Silver, Yellow, Violet, Violet
                ['v', 't', 't', 'o'], # 4: Violet, Teal, Teal, Orange
                ['v', 'b', 'n', 'n'], # 5: Violet, Blue, Brown, Brown
                # Middle Row (6 screws)
                ['l', 'r', 'y', 'g'], # 6: Lime, Red, Yellow, Green
                ['n', 'n', 'd', 'o'], # 7: Brown, Brown, Sand, Orange
                ['c', 'c', 'y', 'c'], # 8: Cyan, Cyan, Yellow, Cyan
                ['p', 'd', 'd', 'c'], # 9: Pink, Sand, Sand, Cyan
                ['g', 'l', 'b', 'b'], # 10: Green, Lime, Blue, Blue
                ['g', 'l', 'o', 'o'], # 11: Green, Lime, Orange, Orange
                # Bottom Row (5 screws)
                ['b', 'v', 'v', 's'], # 12: Blue, Violet, Violet, Silver
                ['r', 'p', 'd', 'r'], # 13: Red, Pink, Sand, Red
                ['y', 'c', 'p', 't'], # 14: Yellow, Cyan, Pink, Teal
                [],                   # 15: Empty
                []                    # 16: Empty
            ]
        elif level == 10:
            # New Level 10: 12 screws (10 filled, 2 empty), capacity 8
            # Colors: 10 distinct colors
            # Layout: 3 Rows of 4
            self.screw_capacity = 8
            self.num_screws = 12
            self.screws = [
                # Row 1
                ['v', 'v', 'b', 'n', 'o', 'n', 'g', 'g'], # 1
                ['v', 'p', 'b', 'o', 'c', 'p', 'y', 'y'], # 2
                ['b', 'n', 'g', 'g', 'r', 'p', 'y', 'y'], # 3
                ['n', 'g', 'o', 'o', 'n', 'b', 'p', 'p'], # 4
                # Row 2
                ['b', 'b', 'c', 'y', 'y', 'c', 'p', 'p'], # 5
                ['o', 'b', 'r', 'v', 'g', 'b', 'b', 'b'], # 6
                ['o', 'r', 'v', 'p', 'p', 'g', 'c', 'c'], # 7
                ['b', 'v', 'p', 'n', 'o', 'v', 'v', 'v'], # 8
                # Row 3
                ['b', 'y', 'g', 'c', 'n', 'g', 'y', 'y'], # 9
                ['r', 'n', 'v', 'c', 'n', 'o', 'y', 'y'], # 10
                [], # 11
                []  # 12
            ]
            
        self._save_state()

    def valid_actions(self) -> list[str]:
        if self.game_over:
            if self.won and self.current_level < self.max_level:
                return ["next_level"]
            return []
            
        actions = []
        
        # Can undo if has undos and history has more than 1 state
        if self.undos_remaining > 0 and len(self.history) > 1:
            actions.append("undo")
            
        # New format: generate all valid "move_A_B" actions
        for src_idx in range(self.num_screws):
            if len(self.screws[src_idx]) > 0:
                for dst_idx in range(self.num_screws):
                    if src_idx != dst_idx and self._is_valid_move(src_idx, dst_idx):
                        actions.append(f"move_{src_idx}_{dst_idx}")
                        
        return actions

    def get_rules(self) -> str:
        return """Nuts and Bolts Game Rules

OBJECTIVE:
Sort all the colored nuts so that each screw contains only one color of nuts.

GAMEPLAY:
- You have 5 screws. Originally, 3 screws are filled with mixed nuts, and 2 are empty.
- Each screw can hold up to 3 nuts format Level 1 and 4 for Level 2.
- You can move the top nut from one screw to another.
- A nut can only be moved onto an empty screw, OR onto a screw where the top nut is the SAME COLOR.
- You cannot move a nut onto a full screw.
- You have 2 Undo moves available per game.

AVAILABLE ACTIONS:
- "select_X": Selects screw X (0-4 or 0-5) as a source, or moves the previously selected nut to screw X.
- "undo": Reverts the last move.
- "next_level": Go to the next level when won.
"""

    # ── Internal helpers ────────────────────────────────────────────

    def _save_state(self) -> None:
        """Save the current board state to history."""
        # Only keep the last state for Undo
        self.history.append({
            "board": deepcopy(self.screws),
            "score": self.score
        })

    def _apply_undo(self) -> None:
        """Revert to the previous state."""
        if self.undos_remaining > 0 and len(self.history) > 1:
            # Remove current state
            self.history.pop()
            # Restore previous state
            prev_state = self.history[-1]
            self.screws = deepcopy(prev_state["board"])
            self.score = deepcopy(prev_state["score"])
            self.undos_remaining -= 1
            self.selected_screw = None

    def _is_valid_move(self, src: int | None, dst: int) -> bool:
        """Check if moving top nut from src to dst is valid."""
        if src is None:
            return False
            
        if src == dst:
            return False
            
        if len(self.screws[src]) == 0:
            return False # Nothing to move
            
        if len(self.screws[dst]) >= self.screw_capacity:
            return False # Destination full
            
        if len(self.screws[dst]) == 0:
            return True # Target is empty, can move any color
            
        # Check if colors match
        src_color = self.screws[src][-1]
        dst_color = self.screws[dst][-1]
        
        return src_color == dst_color

    def _update_score(self) -> None:
        """Update score: 10 points for each full screw with nuts of the same color."""
        completed_towers = 0
        for screw in self.screws:
            if len(screw) == self.screw_capacity:
                first_color = screw[0]
                if all(n == first_color for n in screw):
                    completed_towers += 1
        self.score = completed_towers * 10

    def _move(self, src: int | None, dst: int) -> bool:
        """Execute a move if valid."""
        if src is None or not self._is_valid_move(src, dst):
            return False
            
        # Save state BEFORE making the move
        self._save_state()
        
        nut = self.screws[src].pop()
        self.screws[dst].append(nut)
        
        # Update score after move
        self._update_score()
        return True

    def _move_continuous(self, src_idx: int, dst_idx: int) -> bool:
        """
        Move continuous same-color nuts from src_screw to dst_screw.
        """
        if not self._is_valid_move(src_idx, dst_idx):
            return False
            
        self._save_state()
        
        src_screw = self.screws[src_idx]
        dst_screw = self.screws[dst_idx]
        
        # Get the color of the top nut
        color = src_screw[-1]
        
        # Count how many nuts of this color are continuous at the top
        count = 0
        for i in range(len(src_screw) - 1, -1, -1):
            if src_screw[i] == color:
                count += 1
            else:
                break
                
        # Calculate how many nuts we can actually move based on dst capacity
        available_space = self.screw_capacity - len(dst_screw)
        nuts_to_move = min(count, available_space)
        
        # Move the nuts
        for _ in range(nuts_to_move):
            nut = src_screw.pop()
            dst_screw.append(nut)
            
        self._update_score()
        return True

    def _check_win_condition(self) -> None:
        """Check if all nuts are sorted by color."""
        # Game is won if there are sufficient completed towers
        # and no partially filled towers.
        
        target_towers = 0
        if self.current_level == 1:
            target_towers = 2
        elif self.current_level == 2:
            target_towers = 3
        elif self.current_level == 3:
            target_towers = 4
        elif self.current_level == 4:
            target_towers = 6
        elif self.current_level == 5:
            target_towers = 7
        elif self.current_level == 6:
            target_towers = 14
        elif self.current_level == 7:
            target_towers = 12
        elif self.current_level == 8:
            target_towers = 9
        elif self.current_level == 9:
            target_towers = 14
        else:
            target_towers = 10
        completed_towers = 0
        
        for screw in self.screws:
            if len(screw) == 0:
                continue
                
            # If not empty, it must have full capacity 
            # and they must all be the same color
            if len(screw) == self.screw_capacity:
                first_color = screw[0]
                if all(n == first_color for n in screw):
                    completed_towers += 1
                else:
                    return # Not completed
            else:
                return # Not completed, sizes must be 0 or max capacity
                
        if completed_towers == target_towers:
            self.won = True
