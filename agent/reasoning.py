"""Reasoning module - abstract interface for language models and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
import os
import litellm


class Reasoning(ABC):
    """
    Abstract base class for reasoning engines.
    
    This interface allows easy swapping of different language models
    (GPT, Claude, local models, etc.) without changing the Agent code.
    """
    
    @abstractmethod
    def reason(self, game_state: dict[str, Any], valid_actions: list[str]) -> str:
        """
        Given the current game state and valid actions, reason about the best action.
        
        Args:
            game_state: Current game state dictionary from backend
            valid_actions: List of currently valid action strings
            
        Returns:
            Action string to execute (must be one of valid_actions)
        """
        pass


class LiteLLMReasoning(Reasoning):
    """
    LiteLLM-based reasoning implementation.
    
    Uses LiteLLM to support multiple LLM providers (OpenAI, Anthropic, Google, local models, etc.).
    Model format examples:
    - OpenAI: "gpt-3.5-turbo", "gpt-4"
    - Anthropic: "claude-3-opus-20240229", "claude-3-sonnet-20240229"
    - Google: "gemini/gemini-pro"
    - Local (Ollama): "ollama/llama2"
    - Azure OpenAI: "azure/gpt-4"
    """
    
    def __init__(
        self,
        model: str = "gpt-3.5-turbo",
        api_key: str | None = None,
        api_base: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 50,
    ):
        """
        Initialize LiteLLM reasoning engine.
        
        Args:
            model: Model identifier (supports multiple providers via LiteLLM)
            api_key: API key (if None, LiteLLM will read from environment variables)
            api_base: Optional API base URL (for local models or custom endpoints)
            temperature: Sampling temperature (default: 0.7)
            max_tokens: Maximum tokens in response (default: 50)
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Set API key if provided
        # LiteLLM automatically reads from environment variables
        # We set the appropriate env var based on model provider
        if api_key:
            if model.startswith("gpt") or model.startswith("azure/"):
                os.environ["OPENAI_API_KEY"] = api_key
            elif model.startswith("claude"):
                os.environ["ANTHROPIC_API_KEY"] = api_key
            elif model.startswith("gemini"):
                os.environ["GEMINI_API_KEY"] = api_key
            elif model.startswith("ollama"):
                # Ollama doesn't require API key, but we can set base URL
                pass
            else:
                # Default to OpenAI for backward compatibility
                os.environ["OPENAI_API_KEY"] = api_key
        
        # Set API base if provided (useful for local models or custom endpoints)
        if api_base:
            if model.startswith("ollama"):
                os.environ["OLLAMA_API_BASE"] = api_base
            else:
                # For other providers, use OPENAI_API_BASE (LiteLLM supports this)
                os.environ["OPENAI_API_BASE"] = api_base
        
        # Configure LiteLLM
        litellm.set_verbose = False  # Set to True for debugging
    
    def reason(self, game_state: dict[str, Any], valid_actions: list[str]) -> str:
        """
        Use LiteLLM to reason about the best action given the game state.
        
        Args:
            game_state: Current game state dictionary
            valid_actions: List of valid actions
            
        Returns:
            Selected action string
        """
        # Build prompt
        game_name = game_state.get("game", "unknown")
        board = game_state.get("board", [])
        score = game_state.get("score", 0)
        game_over = game_state.get("game_over", False)
        
        prompt = f"""You are playing the game "{game_name}".

Current game state:
- Score: {score}
- Game Over: {game_over}
- Board:
{self._format_board(board)}

Valid actions you can take: {', '.join(valid_actions)}

Please analyze the current situation and choose the best action from the valid actions list.
Respond with ONLY the action string (e.g., "up", "down", "left", "right", or "drop 0", etc.).
Do not include any explanation or additional text."""

        try:
            # Use LiteLLM to call the model
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a game-playing AI agent. Respond with only the action string."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            action = response.choices[0].message.content.strip()
            
            # Validate that the action is in valid_actions
            if action not in valid_actions:
                # If model returned an invalid action, fallback to first valid action
                print(f"Warning: Model returned invalid action '{action}', using first valid action instead")
                action = valid_actions[0] if valid_actions else ""
            
            return action
            
        except Exception as e:
            print(f"Error calling model ({self.model}): {e}")
            # Fallback to first valid action on error
            return valid_actions[0] if valid_actions else ""
    
    def _format_board(self, board: Any) -> str:
        """Format board for display in prompt."""
        if isinstance(board, list):
            if len(board) > 0 and isinstance(board[0], list):
                # 2D board
                return "\n".join(" ".join(str(cell) for cell in row) for row in board)
            else:
                # 1D board
                return " ".join(str(cell) for cell in board)
        return str(board)


# Backward compatibility alias
GPTReasoning = LiteLLMReasoning
