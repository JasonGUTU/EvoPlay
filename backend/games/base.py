"""Abstract base class for all games in EvoPlay."""

from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

# All log files go here (relative to backend/)
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


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
      - Every game session writes to  logs/<game>/<timestamp>.jsonl
    """

    # Subclasses should set  name = "xxx"
    name: str = "unknown"

    # ── Log internals ───────────────────────────────────────────────

    def _reset_log(self) -> None:
        """Initialise (or reset) the in-memory log and open a new log file."""
        self._log: list[dict[str, Any]] = []
        self._steps: int = 0
        self._start_time: float | None = None

        # Close previous log file if open
        if hasattr(self, "_log_file") and self._log_file is not None:
            try:
                self._log_file.close()
            except Exception:
                pass

        # Create a new log file: logs/<game>/20260213_153045.jsonl
        game_log_dir = LOG_DIR / self.name
        game_log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self._log_path = game_log_dir / ("%s.jsonl" % ts)
        self._log_file = open(self._log_path, "w", encoding="utf-8")

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

        # Write to file (one JSON object per line)
        if hasattr(self, "_log_file") and self._log_file is not None:
            self._log_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
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
