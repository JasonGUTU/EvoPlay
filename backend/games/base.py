"""Abstract base class for all games in EvoPlay."""

from __future__ import annotations

import csv
import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

# All log files go here (relative to backend/)
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
# Save files for resuming unfinished games
SAVE_DIR = Path(__file__).resolve().parent.parent / "saves"


class BaseGame(ABC):
    """
    Every game must implement this interface.

    Contract:
      - get_state()  -> dict   : full JSON-serialisable snapshot of the game.
      - apply_action(action)   : mutate internal state; return new state dict.
      - reset()                : restart the game; return initial state dict.
      - valid_actions()        : list of currently legal action strings.

    Built-in logging:
      - _log / _steps / _start_time are managed automatically.
      - Subclasses call self._record_log(action, state) after each action.
      - get_log_info() returns {log, steps, elapsed_seconds}.
      - Every game session writes to logs/<game>/<session_id>.csv (CSV format)
      - Log file is created lazily on first log entry (avoids empty files)
      - CSV format: step, time, action, score, game_over, board (board stored as JSON string)
    """

    # Subclasses should set  name = "xxx"
    name: str = "unknown"
    
    # Session ID for log file naming (set by backend when creating game instance)
    _session_id: str | None = None
    # Player name associated with this session
    _player_name: str | None = None

    # ── Log internals ───────────────────────────────────────────────

    def set_session_id(self, session_id: str) -> None:
        """Set session ID for this game instance (used for log file naming)."""
        self._session_id = session_id

    def set_player_name(self, player_name: str) -> None:
        """Set player name for this game instance (recorded in logs)."""
        self._player_name = player_name

    def _reset_log(self) -> None:
        """Initialise (or reset) the in-memory log. Log file is created lazily on first write."""
        self._log: list[dict[str, Any]] = []
        self._steps: int = 0
        self._start_time: float | None = None

        # Close previous log file if open
        if hasattr(self, "_log_file") and self._log_file is not None:
            try:
                self._log_file.close()
            except Exception:
                pass
        self._log_file = None
        self._log_path = None

        # Increment round counter so each game gets a unique log file
        if not hasattr(self, "_round"):
            self._round = 0
        self._round += 1

    def _ensure_log_file(self) -> None:
        """Create log file if it doesn't exist yet. Called lazily on first log entry."""
        if self._log_file is not None:
            return
        
        if not self._session_id:
            # Fallback to timestamp if session_id not set (shouldn't happen in normal flow)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            log_filename = f"{ts}.csv"
        else:
            # Use session_id as filename (sanitize for filesystem)
            # Replace characters that might be problematic in filenames
            safe_session_id = self._session_id.replace("/", "_").replace("\\", "_")
            rd = getattr(self, "_round", 1)
            log_filename = f"{safe_session_id}_r{rd}.csv"
        
        player = (self._player_name or "unknown").replace("/", "_").replace("\\", "_")
        game_log_dir = LOG_DIR / self.name / player
        game_log_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = game_log_dir / log_filename
        self._log_file = open(self._log_path, "w", encoding="utf-8", newline="")
        
        # Write CSV header
        writer = csv.writer(self._log_file)
        writer.writerow(["step", "timestamp", "time", "game", "player", "difficulty", "level", "action", "score", "game_over", "board"])

    def _record_log(self, action: str, state: dict[str, Any]) -> None:
        """Append one log entry to memory and flush to disk."""
        now = time.time()
        if self._start_time is None:
            self._start_time = now

        self._steps += 1
        entry = {
            "step": self._steps,
            "time": round(now - self._start_time, 2),
            "action": action,
            "score": state.get("score", 0),
            "game_over": state.get("game_over", False),
            "board": state.get("board"),
        }
        self._log.append(entry)

        # Create log file lazily on first write (avoids empty files)
        self._ensure_log_file()

        # Write to CSV file
        if self._log_file is not None:
            writer = csv.writer(self._log_file)
            # Convert board to JSON string for CSV storage
            board_str = json.dumps(entry["board"], ensure_ascii=False) if entry["board"] else ""
            difficulty = getattr(self, "difficulty", "")
            level = getattr(self, "current_level", "")
            writer.writerow([
                entry["step"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                entry["time"],
                self.name,
                self._player_name or "",
                difficulty,
                level,
                entry["action"],
                entry["score"],
                entry["game_over"],
                board_str
            ])
            self._log_file.flush()

    def get_log_info(self) -> dict[str, Any]:
        """Return log metadata for the API response."""
        elapsed = 0.0
        if self._start_time is not None:
            elapsed = round(time.time() - self._start_time, 2)
        return {
            "steps": self._steps,
            "elapsed_seconds": elapsed,
            "log": list(self._log),
        }

    def get_metrics(self) -> dict[str, Any]:
        """
        Return game-specific tracking metrics for analytics.
        By default, it returns steps and final score.
        Subclasses should override this to include game-specific data.
        """
        return {
            "steps": self._steps,
            "score": getattr(self, "score", 0),
            "game_over": getattr(self, "game_over", False),
            "won": getattr(self, "won", False)
        }

    # ── Save / Resume ─────────────────────────────────────────────

    def serialize(self) -> dict[str, Any]:
        """Serialize game state to a JSON-friendly dict for persistence.
        Subclasses can override to include game-specific fields."""
        return {
            "name": self.name,
            "state": self.get_state(),
            "session_id": self._session_id,
            "player_name": self._player_name,
            "difficulty": getattr(self, "difficulty", ""),
            "steps": self._steps,
        }

    def save(self) -> None:
        """Save current game state to disk for later resumption."""
        if not self._player_name or not self.name:
            return
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        safe_player = self._player_name.replace("/", "_").replace("\\", "_")
        save_path = SAVE_DIR / f"{safe_player}_{self.name}.json"
        data = self.serialize()
        data["game_over"] = getattr(self, "game_over", False)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    @staticmethod
    def load_save(player_name: str, game_name: str) -> dict[str, Any] | None:
        """Load saved game state from disk. Returns None if no save exists or game was finished."""
        safe_player = player_name.replace("/", "_").replace("\\", "_")
        save_path = SAVE_DIR / f"{safe_player}_{game_name}.json"
        if not save_path.exists():
            return None
        try:
            with open(save_path, encoding="utf-8") as f:
                data = json.load(f)
            # Don't resume finished games
            if data.get("game_over", False):
                return None
            return data
        except Exception:
            return None

    def restore_state(self, saved_state: dict[str, Any]) -> None:
        """Restore game state from a saved state dict.
        Works for most games by setting common attributes from the state."""
        if "board" in saved_state:
            self.board = saved_state["board"]
        if "score" in saved_state:
            self.score = saved_state["score"]
        if "game_over" in saved_state:
            self.game_over = saved_state["game_over"]
        if "won" in saved_state:
            self.won = saved_state.get("won", False)
        if "difficulty" in saved_state and hasattr(self, "set_difficulty"):
            self.set_difficulty(saved_state["difficulty"])
        # Game-specific fields
        if "max_tile" in saved_state and hasattr(self, "max_tile"):
            self.max_tile = saved_state["max_tile"]
        if "next_tile" in saved_state and hasattr(self, "next_tile"):
            self.next_tile = saved_state["next_tile"]
        if "moves" in saved_state and hasattr(self, "moves"):
            self.moves = saved_state["moves"]

    @staticmethod
    def delete_save(player_name: str, game_name: str) -> None:
        """Delete saved game state (called when game is finished or reset)."""
        safe_player = player_name.replace("/", "_").replace("\\", "_")
        save_path = SAVE_DIR / f"{safe_player}_{game_name}.json"
        if save_path.exists():
            save_path.unlink()

    # ── Abstract interface ──────────────────────────────────────────

    @abstractmethod
    def get_state(self) -> dict[str, Any]:
        """Return the current game state as a JSON-friendly dict."""

    @abstractmethod
    def apply_action(self, action: str) -> dict[str, Any]:
        """
        Apply *action* (e.g. "up", "left", "3") and return the new state.

        If the action is invalid or the game is over the implementation
        should still return the current state (optionally with an "error" key).
        """

    @abstractmethod
    def reset(self) -> dict[str, Any]:
        """Reset the game to its initial state and return that state."""

    @abstractmethod
    def valid_actions(self) -> list[str]:
        """Return the list of action strings that are currently legal."""
    
    @abstractmethod
    def get_rules(self) -> str:
        """
        Return a string describing the game rules.
        
        This should include:
        - Game objective and gameplay
        - Specific rules
        - Available actions and how to use them
        - Game over conditions
        """