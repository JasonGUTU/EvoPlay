"""Base class for reasoning engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Reasoning(ABC):
    """
    Abstract base class for reasoning engines.
    
    This interface allows easy swapping of different reasoning methods
    (direct LLM calls, agent-based reasoning, etc.) without changing the Agent code.
    """
    
    @abstractmethod
    def reason(self, game_state: dict[str, Any], valid_actions: list[str], rules: str = "") -> str:
        """
        Given the current game state and valid actions, reason about the best action.
        
        Args:
            game_state: Current game state dictionary from backend
            valid_actions: List of currently valid action strings
            rules: Game rules description string
            
        Returns:
            Action string to execute (must be one of valid_actions)
        """
        pass
