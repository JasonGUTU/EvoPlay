"""Sokoban game implementation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, List, Tuple

from .base import BaseGame

# Map layout from image:
# #####
# #@  #
# # O$#
# # $ ###
# #   ..#
# #######

# Internal representation:
# ' ' = Floor
# '#' = Wall
# 'O' = Obstacle (treat as Wall for movement)
# 'W' = Water Obstacle (treat as Wall for movement)
# '.' = Goal

INITIAL_MAP = [
    ['#', '#', '#', '#', '#', ' ', ' '],
    ['#', ' ', ' ', ' ', '#', ' ', ' '],
    ['#', ' ', 'O', ' ', '#', ' ', ' '],
    ['#', ' ', ' ', ' ', '#', '#', '#'],
    ['#', ' ', ' ', ' ', '.', '.', '#'],
    ['#', '#', '#', '#', '#', '#', '#'],
]

INITIAL_PLAYER_POS = [1, 1]
INITIAL_BOXES = [[2, 3], [3, 2]]
MAX_UNDOS = 1

VALID_DIFFICULTIES = {"easy", "medium", "hard"}

class Sokoban(BaseGame):
    """Classic Sokoban box-pushing game."""

    name = "sokoban"

    def __init__(self) -> None:
        self.map: list[list[str]] = []
        self.player_pos: list[int] = []
        self.boxes: list[list[int]] = []
        self.score: int = 0
        self.game_over: bool = False
        self.won: bool = False
        self.withdrawn: bool = False
        self.undo_available: bool = True
        self.history: dict[str, Any] | None = None
        
        self.current_level: int = 1
        self.max_level: int = 10
        self.difficulty: str = "easy"
        
        self._reset_log()
        self.reset()

    def set_difficulty(self, difficulty: str) -> None:
        if difficulty in VALID_DIFFICULTIES:
            self.difficulty = difficulty
            # Map difficulty to starting level
            if difficulty == "easy":
                self.current_level = 1
            elif difficulty == "medium":
                self.current_level = 5
            elif difficulty == "hard":
                self.current_level = 8
            self.reset()

    # ── BaseGame interface ──────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        return {
            "game": self.name,
            "board": {
                "map": self.map,
                "player_pos": self.player_pos,
                "boxes": self.boxes
            },
            "score": self.score,
            "game_over": self.game_over,
            "won": self.won,
            "withdrawn": self.withdrawn,
            "valid_actions": self.valid_actions(),
            "undo_available": self.undo_available,
            "current_level": self.current_level,
            "max_level": self.max_level,
            "difficulty": self.difficulty
        }

    def apply_action(self, action: str) -> dict[str, Any]:
        action = action.strip().lower()

        if self.game_over and action != "next_level":
            state = self.get_state()
            state["error"] = "Game is already over."
            return state

        if action != "withdraw" and action not in self.valid_actions():
            state = self.get_state()
            state["error"] = f"Invalid action: {action}"
            return state

        if action == "undo":
            self._apply_undo()
        elif action == "withdraw":
            self.withdrawn = True
            self.game_over = True
        elif action == "next_level":
            self.current_level += 1
            self._load_level(self.current_level)
        elif action in ["up", "down", "left", "right"]:
            self._move(action)
        
        state = self.get_state()
        self._record_log(action, state)
        return state

    def reset(self) -> dict[str, Any]:
        self._reset_log()
        self._load_level(self.current_level)
        return self.get_state()
        
    def _load_level(self, level: int) -> None:
        if level == 1:
            self.map = [
                ['#', '#', '#', '#', '#', '#', '#'],
                ['#', ' ', ' ', ' ', ' ', '.', '#'],
                ['#', '#', '#', '#', '#', '#', '#']
            ]
            self.player_pos = [1, 1]
            self.boxes = [[1, 3]]
        elif level == 2:
            self.map = deepcopy(INITIAL_MAP)
            self.player_pos = deepcopy(INITIAL_PLAYER_POS)
            self.boxes = deepcopy(INITIAL_BOXES)
        elif level == 3:
            # Level 3 map
            self.map = [
                ['#', '#', '#', '#', '#', '#', '#'],
                ['#', '.', ' ', ' ', ' ', '.', '#'],
                ['#', ' ', ' ', ' ', ' ', ' ', '#'],
                ['#', ' ', ' ', ' ', ' ', ' ', '#'],
                ['#', ' ', ' ', ' ', ' ', ' ', '#'],
                ['#', '.', ' ', ' ', ' ', '.', '#'],
                ['#', '#', '#', '#', '#', '#', '#']
            ]
            self.player_pos = [3, 3] # Center
            self.boxes = [
                [2, 3], # Top
                [4, 3], # Bottom
                [3, 2], # Left
                [3, 4]  # Right
            ]
        elif level == 4:
            self.map = [
                ['#', '#', '#', '#', '#', '#', '#'],
                ['#', '.', ' ', ' ', ' ', '.', '#'],
                ['#', ' ', ' ', ' ', ' ', ' ', '#'],
                ['#', '.', ' ', ' ', ' ', '.', '#'],
                ['#', '#', '#', '#', '#', '#', '#']
            ]
            self.player_pos = [2, 3] # Center
            self.boxes = [
                [1, 3], # Top
                [3, 3], # Bottom
                [2, 2], # Left
                [2, 4]  # Right
            ]
        elif level == 5:
            self.map = [
                ['#', '#', '#', '#', '#', '#', '#', '#', '#'],
                ['#', '.', ' ', ' ', ' ', ' ', ' ', '.', '#'],
                ['#', ' ', 'O', ' ', '.', ' ', 'W', ' ', '#'],
                ['#', ' ', ' ', ' ', ' ', ' ', ' ', ' ', '#'],
                ['#', ' ', ' ', ' ', ' ', ' ', ' ', ' ', '#'],
                ['#', ' ', ' ', ' ', ' ', ' ', ' ', ' ', '#'],
                ['#', ' ', 'W', ' ', '.', ' ', 'O', ' ', '#'],
                ['#', '.', ' ', ' ', ' ', ' ', ' ', '.', '#'],
                ['#', '#', '#', '#', '#', '#', '#', '#', '#']
            ]
            self.player_pos = [4, 4] # Center
            self.boxes = [
                [2, 4], # Top outer
                [3, 4], # Top inner
                [5, 4], # Bottom inner
                [6, 4], # Bottom outer
                [4, 3], # Left
                [4, 5]  # Right
            ]
        elif level == 6:
            # Level 6 (Push6) map from image:
            # Inner grid is 6 columns wide, 4 rows high -> Total 8x6 with walls
            # 8 Boxes, 7 Visible Goals.
            # The top row has ONLY ONE goal at col 6.
            self.map = [
                ['#', '#', '#', '#', '#', '#', '#', '#'],
                ['#', ' ', ' ', ' ', ' ', ' ', '.', '#'],
                ['#', ' ', '.', ' ', ' ', ' ', '.', '#'],
                ['#', ' ', ' ', '.', ' ', ' ', '.', '#'],
                ['#', ' ', '.', ' ', ' ', ' ', '.', '#'],
                ['#', '#', '#', '#', '#', '#', '#', '#']
            ]
            self.player_pos = [2, 1] 
            self.boxes = [
                [1, 2],         [1, 5],
                [2, 3],         [2, 5],
                [3, 2],         [3, 5],
                [4, 3],         [4, 5]
            ]
        elif level == 7:
            # Level 7 (Push7) map from image:
            # 7x7 grid, cross-shaped interior (fat cross)
            # Player in center, surrounded by 8 boxes in a 3x3 area.
            # 8 goals at the inner corners of the cross.
            self.map = [
                ['#', '#', '#', '#', '#', '#', '#'],
                ['#', '#', '.', ' ', '.', '#', '#'],
                ['#', '.', ' ', ' ', ' ', '.', '#'],
                ['#', ' ', ' ', ' ', ' ', ' ', '#'],
                ['#', '.', ' ', ' ', ' ', '.', '#'],
                ['#', '#', '.', ' ', '.', '#', '#'],
                ['#', '#', '#', '#', '#', '#', '#']
            ]
            self.player_pos = [3, 3] # Center
            self.boxes = [
                [2, 2], [2, 3], [2, 4],
                [3, 2],         [3, 4],
                [4, 2], [4, 3], [4, 4]
            ]
        elif level == 8:
            # Level 8 (Push8) map from image:
            # 5x5 inner grid -> 7x7 total with walls
            self.map = [
                ['#', '#', '#', '#', '#', '#', '#'],
                ['#', '.', ' ', ' ', '.', '.', '#'],
                ['#', '.', ' ', ' ', ' ', ' ', '#'],
                ['#', ' ', ' ', 'W', ' ', ' ', '#'],
                ['#', ' ', ' ', ' ', ' ', '.', '#'],
                ['#', '.', '.', ' ', ' ', '.', '#'],
                ['#', '#', '#', '#', '#', '#', '#']
            ]
            self.player_pos = [4, 2] # r=3, c=1 in inner grid -> r=4, c=2 in 7x7 grid
            self.boxes = [
                [1, 3], # r=0, c=2
                [2, 3], # r=1, c=2
                [3, 1], # r=2, c=0
                [3, 2], # r=2, c=1
                [3, 4], # r=2, c=3
                [3, 5], # r=2, c=4
                [4, 3], # r=3, c=2
                [5, 3]  # r=4, c=2
            ]
        elif level == 9:
            # Level 9 (Push9) map from image:
            # Small 5x5-ish map with 2 boxes and 2 goals.
            # Goals: (1, 2) (visible blue circle) and (2, 1) (inferred under Cyan Box).
            # Boxes: (2, 1) (Cyan) and (3, 2) (Orange).
            # Player: (2, 2).
            # To be solvable, (4, 3) must be floor.
            self.map = [
                ['#', '#', '#', '#', '#'],
                ['#', ' ', '.', '#', '#'],
                ['#', '.', ' ', '#', '#'],
                ['#', ' ', ' ', ' ', '#'],
                ['#', ' ', ' ', ' ', '#'],
                ['#', '#', '#', '#', '#']
            ]
            self.player_pos = [2, 2]
            self.boxes = [
                [2, 1], # Starts on goal (Cyan)
                [3, 2]  # Orange
            ]
        elif level == 10:
            # Level 10 (Push10) map from image:
            # 9x9 grid (7x7 inner)
            # Player center. 8 Boxes surrounding player.
            # Goals: 4 corners + 4 inner side positions.
            # Obstacles: Water (left), Rope (right).
            self.map = [
                ['#', '#', '#', '#', '#', '#', '#', '#', '#'],
                ['#', '.', ' ', ' ', ' ', ' ', ' ', '.', '#'],
                ['#', ' ', 'W', ' ', ' ', ' ', 'O', ' ', '#'],
                ['#', ' ', '.', ' ', ' ', ' ', '.', ' ', '#'],
                ['#', ' ', ' ', ' ', ' ', ' ', ' ', ' ', '#'],
                ['#', ' ', '.', ' ', ' ', ' ', '.', ' ', '#'],
                ['#', ' ', 'W', ' ', ' ', ' ', 'O', ' ', '#'],
                ['#', '.', ' ', ' ', ' ', ' ', ' ', '.', '#'],
                ['#', '#', '#', '#', '#', '#', '#', '#', '#']
            ]
            self.player_pos = [4, 4]
            self.boxes = [
                [3, 3], [3, 4], [3, 5],
                [4, 3],         [4, 5],
                [5, 3], [5, 4], [5, 5]
            ]

        self.score = 0
        self.game_over = False
        self.won = False
        self.withdrawn = False
        self.undo_available = True
        self.history = None

    def valid_actions(self) -> list[str]:
        if self.game_over:
            if (self.won or self.withdrawn) and self.current_level < self.max_level:
                return ["next_level"]
            return []
            
        actions = []
        
        if self.undo_available and self.history is not None:
            actions.append("undo")
            
        for direction in ["up", "down", "left", "right"]:
            if self._can_move(direction):
                actions.append(direction)
                    
        return actions

    def get_rules(self) -> str:
        return """Sokoban Game Rules

OBJECTIVE:
Push all boxes onto the goal squares.

GAMEPLAY:
- You control the player character (hardhat worker).
- You can move up, down, left, or right into empty spaces.
- You can push a single box by moving into it, provided the space behind the box is empty or a goal.
- You CANNOT pull boxes.
- You CANNOT push a box into a wall, the rope obstacle, or another box.
- You have 1 Undo available per game.

AVAILABLE ACTIONS:
- "up", "down", "left", "right": Move the player or push a box.
- "undo": Reverts the last move.
"""

    # ── Internal helpers ────────────────────────────────────────────

    def _save_state(self) -> None:
        """Save the current state to history."""
        self.history = {
            "player_pos": deepcopy(self.player_pos),
            "boxes": deepcopy(self.boxes),
            "score": self.score
        }

    def _apply_undo(self) -> None:
        """Revert to the previous state."""
        history = self.history
        if self.undo_available and history is not None:
            self.player_pos = deepcopy(history["player_pos"])
            self.boxes = deepcopy(history["boxes"])
            self.score = history["score"]
            self.undo_available = False # Only 1 undo allowed
            self.history = None

    def _get_delta(self, direction: str) -> tuple[int, int]:
        if direction == "up": return -1, 0
        if direction == "down": return 1, 0
        if direction == "left": return 0, -1
        if direction == "right": return 0, 1
        return 0, 0
        
    def _is_walkable(self, r: int, c: int) -> bool:
        if r < 0 or r >= len(self.map) or c < 0 or c >= len(self.map[0]):
            return False
        return self.map[r][c] in [' ', '.']

    def _get_box_index(self, r: int, c: int) -> int | None:
        for i, box in enumerate(self.boxes):
            if box[0] == r and box[1] == c:
                return i
        return None

    def _can_move(self, direction: str) -> bool:
        dr, dc = self._get_delta(direction)
        nr, nc = self.player_pos[0] + dr, self.player_pos[1] + dc
        
        if not self._is_walkable(nr, nc):
            return False
            
        box_idx = self._get_box_index(nr, nc)
        if box_idx is not None:
            # Check space behind box
            nnr, nnc = nr + dr, nc + dc
            if not self._is_walkable(nnr, nnc):
                return False
            if self._get_box_index(nnr, nnc) is not None:
                return False
                
        return True

    def _update_score(self) -> None:
        """Update score: 10 points for each box on a goal."""
        goals = []
        for r in range(len(self.map)):
            for c in range(len(self.map[r])):
                if self.map[r][c] == '.':
                    goals.append([r, c])
                    
        goals_covered = 0
        for goal in goals:
            for box in self.boxes:
                if box[0] == goal[0] and box[1] == goal[1]:
                    goals_covered += 1
                    break
                    
        self.score = goals_covered * 10

    def _move(self, direction: str) -> None:
        if not self._can_move(direction):
            return
            
        self._save_state()
        
        dr, dc = self._get_delta(direction)
        nr, nc = self.player_pos[0] + dr, self.player_pos[1] + dc
        
        box_idx = self._get_box_index(nr, nc)
        if box_idx is not None:
            # Push the box
            box = self.boxes[box_idx]
            box[0] = box[0] + dr
            box[1] = box[1] + dc
            
        self.player_pos = [nr, nc]
        
        # Update score after move
        self._update_score()
        self._check_win_condition()

    def _check_win_condition(self) -> None:
        """Check if all boxes are on goals."""
        goals = []
        for r in range(len(self.map)):
            for c in range(len(self.map[r])):
                if self.map[r][c] == '.':
                    goals.append([r, c])
                    
        # Check if every goal is covered by a box
        goals_covered = 0
        for goal in goals:
            for box in self.boxes:
                if box[0] == goal[0] and box[1] == goal[1]:
                    goals_covered += 1
                    break
                    
        # Win if all goals are covered
        if len(goals) > 0 and goals_covered == len(goals):
            self.won = True
            self.game_over = True
