"""Reasoning module - different reasoning methods for game agents."""

from __future__ import annotations

from .base import Reasoning
from .vanilla_reasoning import VanillaReasoning

# Backward compatibility aliases
LiteLLMReasoning = VanillaReasoning
GPTReasoning = VanillaReasoning

__all__ = [
    "Reasoning",
    "VanillaReasoning",
    "LiteLLMReasoning",  # Backward compatibility
    "GPTReasoning",  # Backward compatibility
]
