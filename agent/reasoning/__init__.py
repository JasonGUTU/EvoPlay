"""Reasoning module - different reasoning methods for game agents."""

from __future__ import annotations

from .base import Reasoning
from .vanilla_reasoning import VanillaReasoning
from .rl_reasoning import RLReasoning

# Backward compatibility aliases
LiteLLMReasoning = VanillaReasoning
GPTReasoning = VanillaReasoning

__all__ = [
    "Reasoning",
    "VanillaReasoning",
    "RLReasoning",
    "LiteLLMReasoning",  # Backward compatibility
    "GPTReasoning",  # Backward compatibility
]
