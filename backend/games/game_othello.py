"""Othello (Reversi) — human (1, Black) vs. bot (2, White).

Difficulty levels:
  easy   – random valid move
  medium – Minimax depth 3 + positional weight matrix
  hard   – Minimax depth 5 + positional weights + mobility heuristic
"""

from __future__ import annotations

import math
import random
from typing import Any

from .base import BaseGame

SIZE = 8
EMPTY = 0
HUMAN = 1   # Black, moves first
BOT = 2     # White

DIRECTIONS = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

# Classic positional weight table: corners best, X-squares worst
WEIGHTS = [
    [100, -20, 10,  5,  5, 10, -20, 100],
    [-20, -50, -2, -2, -2, -2, -50, -20],
    [ 10,  -2,  1,  1,  1,  1,  -2,  10],
    [  5,  -2,  1,  1,  1,  1,  -2,   5],
    [  5,  -2,  1,  1,  1,  1,  -2,   5],
    [ 10,  -2,  1,  1,  1,  1,  -2,  10],
    [-20, -50, -2, -2, -2, -2, -50, -20],
    [100, -20, 10,  5,  5, 10, -20, 100],
]

VALID_DIFFICULTIES = {"easy", "medium", "hard"}


# ── Pure board functions ──────────────────────────────────────────────

def _opp(piece: int) -> int:
    return BOT if piece == HUMAN else HUMAN


def _get_flips(board: list, r: int, c: int, piece: int) -> list[tuple[int,int]]:
    opp = _opp(piece)
    flips: list[tuple[int,int]] = []
    for dr, dc in DIRECTIONS:
        line: list[tuple[int,int]] = []
        nr, nc = r + dr, c + dc
        while 0 <= nr < SIZE and 0 <= nc < SIZE and board[nr][nc] == opp:
            line.append((nr, nc))
            nr += dr
            nc += dc
        if line and 0 <= nr < SIZE and 0 <= nc < SIZE and board[nr][nc] == piece:
            flips.extend(line)
    return flips


def _valid_moves(board: list, piece: int) -> list[tuple[int,int]]:
    return [
        (r, c)
        for r in range(SIZE)
        for c in range(SIZE)
        if board[r][c] == EMPTY and _get_flips(board, r, c, piece)
    ]


def _apply_move(board: list, r: int, c: int, piece: int) -> list:
    new = [row[:] for row in board]
    new[r][c] = piece
    for fr, fc in _get_flips(new, r, c, piece):
        new[fr][fc] = piece
    return new


def _count(board: list, piece: int) -> int:
    return sum(board[r][c] == piece for r in range(SIZE) for c in range(SIZE))


def _score_positional(board: list, piece: int) -> float:
    opp = _opp(piece)
    score = 0.0
    for r in range(SIZE):
        for c in range(SIZE):
            if board[r][c] == piece:
                score += WEIGHTS[r][c]
            elif board[r][c] == opp:
                score -= WEIGHTS[r][c]
    return score


def _score_full(board: list, piece: int) -> float:
    """Positional weights + mobility."""
    opp = _opp(piece)
    pos = _score_positional(board, piece)
    mob = len(_valid_moves(board, piece)) - len(_valid_moves(board, opp))
    return pos + 10.0 * mob


def _minimax(
    board: list,
    depth: int,
    alpha: float,
    beta: float,
    maximizing: bool,
    bot_piece: int,
    use_mobility: bool,
) -> float:
    current = bot_piece if maximizing else _opp(bot_piece)
    moves = _valid_moves(board, current)

    if not moves:
        opp_moves = _valid_moves(board, _opp(current))
        if not opp_moves:
            # Terminal: count pieces
            bc = _count(board, bot_piece)
            hc = _count(board, _opp(bot_piece))
            return float(bc - hc) * 1000
        # Pass — switch side, don't decrement depth
        return _minimax(board, depth, alpha, beta, not maximizing, bot_piece, use_mobility)

    if depth == 0:
        return _score_full(board, bot_piece) if use_mobility else _score_positional(board, bot_piece)

    if maximizing:
        value = -math.inf
        for r, c in moves:
            value = max(value, _minimax(
                _apply_move(board, r, c, current),
                depth - 1, alpha, beta, False, bot_piece, use_mobility))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value
    else:
        value = math.inf
        for r, c in moves:
            value = min(value, _minimax(
                _apply_move(board, r, c, current),
                depth - 1, alpha, beta, True, bot_piece, use_mobility))
            beta = min(beta, value)
            if alpha >= beta:
                break
        return value


# ── Game class ────────────────────────────────────────────────────────

class Othello(BaseGame):
    name = "othello"

    def __init__(self):
        self.difficulty = "hard"
        self._reset_log()
        self.reset()

    def set_difficulty(self, difficulty: str) -> None:
        if difficulty in VALID_DIFFICULTIES:
            self.difficulty = difficulty

    # ── Public interface ──────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        human_moves = _valid_moves(self.board, HUMAN)
        return {
            "game": self.name,
            "board": [row[:] for row in self.board],
            "score": self.score,
            "game_over": self.game_over,
            "won": self.won,
            "winner": self.winner,
            "difficulty": self.difficulty,
            "human_count": _count(self.board, HUMAN),
            "bot_count": _count(self.board, BOT),
            "valid_moves": [[r, c] for r, c in human_moves],
            "valid_actions": self.valid_actions(),
        }

    def apply_action(self, action: str) -> dict[str, Any]:
        """Apply the human's move only; bot move is triggered separately."""
        if self.game_over:
            return self.get_state()

        try:
            parts = action.strip().split()
            r, c = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            return {**self.get_state(), "error": f"Invalid action format: '{action}' — expected 'row col'"}

        if (r, c) not in _valid_moves(self.board, HUMAN):
            return {**self.get_state(), "error": f"Invalid move: ({r}, {c})"}

        self.board = _apply_move(self.board, r, c, HUMAN)
        self._record_log(f"human:{r},{c}", self.get_state())
        self._resolve_game_over()
        # Signal frontend that bot still needs to move
        state = self.get_state()
        state["bot_pending"] = not self.game_over
        return state

    def apply_bot_move(self) -> dict[str, Any]:
        """Apply the bot's move and return the resulting state with move details."""
        if self.game_over:
            return self.get_state()

        bot_move = self._best_move()
        if bot_move:
            br, bc = bot_move
            flipped = _get_flips(self.board, br, bc, BOT)
            self.board = _apply_move(self.board, br, bc, BOT)
            self._resolve_game_over()
            self._record_log(f"bot:{br},{bc}", self.get_state())
            state = self.get_state()
            state["bot_move_pos"] = [br, bc]
            state["bot_flipped"] = [[r, c] for r, c in flipped]
            return state

        return self.get_state()

    def reset(self) -> dict[str, Any]:
        self.board = [[EMPTY] * SIZE for _ in range(SIZE)]
        mid = SIZE // 2
        self.board[mid-1][mid-1] = BOT
        self.board[mid-1][mid]   = HUMAN
        self.board[mid][mid-1]   = HUMAN
        self.board[mid][mid]     = BOT
        self.game_over = False
        self.won = False
        self.winner = None
        self.score = 0
        self._reset_log()
        return self.get_state()

    def valid_actions(self) -> list[str]:
        if self.game_over:
            return []
        return [f"{r} {c}" for r, c in _valid_moves(self.board, HUMAN)]

    def get_rules(self) -> str:
        return (
            "Othello 8×8. You are Black (1), bot is White (2). "
            "Place a piece to flip all opponent pieces sandwiched between yours. "
            "You must flip at least one piece. "
            "Game ends when neither player can move; most pieces wins. "
            "Action: 'row col' (0-indexed)."
        )

    # ── Helpers ───────────────────────────────────────────────────────

    def _resolve_game_over(self) -> bool:
        if _valid_moves(self.board, HUMAN) or _valid_moves(self.board, BOT):
            return False
        self.game_over = True
        hc = _count(self.board, HUMAN)
        bc = _count(self.board, BOT)
        if hc > bc:
            self.won = True
            self.winner = "human"
            self.score = hc - bc
        elif bc > hc:
            self.winner = "bot"
            self.score = bc - hc
        else:
            self.winner = "draw"
        return True

    def _best_move(self) -> tuple[int,int] | None:
        moves = _valid_moves(self.board, BOT)
        if not moves:
            return None

        if self.difficulty == "easy":
            return random.choice(moves)

        depth = 3 if self.difficulty == "medium" else 5
        use_mobility = (self.difficulty == "hard")

        best_score = -math.inf
        best = moves[0]
        for r, c in moves:
            sc = _minimax(
                _apply_move(self.board, r, c, BOT),
                depth - 1, -math.inf, math.inf,
                False, BOT, use_mobility,
            )
            if sc > best_score:
                best_score = sc
                best = (r, c)
        return best
