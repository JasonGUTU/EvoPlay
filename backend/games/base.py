"""Abstract base class for all games in EvoPlay."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseGame(ABC):
    """
    Every game must implement this interface.

    Contract:
      - get_state()  -> dict   : full JSON-serialisable snapshot of the game.
      - apply_action(action)   : mutate internal state; return new state dict.
      - reset()                : restart the game; return initial state dict.
      - valid_actions()        : list of currently legal action strings.
    """

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
