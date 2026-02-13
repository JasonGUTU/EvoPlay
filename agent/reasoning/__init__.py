"""Reasoning module - different reasoning methods for game agents."""

from __future__ import annotations

from .base import Reasoning
from .litellm_reasoning import LiteLLMReasoning

# Backward compatibility alias
GPTReasoning = LiteLLMReasoning

__all__ = [
    "Reasoning",
    "LiteLLMReasoning",
    "GPTReasoning",
]
