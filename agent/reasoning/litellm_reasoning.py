"""LiteLLM-based reasoning implementation."""

from __future__ import annotations

from typing import Any
import os
import litellm

from .base import Reasoning


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
        api_provider: str | None = None,
        api_base: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 50,
    ):
        """
        Initialize LiteLLM reasoning engine.
        
        Args:
            model: Model identifier (supports multiple providers via LiteLLM)
            api_key: API key (if None, will try to read from config or environment)
            api_provider: API provider name (openai, anthropic, gemini, etc.)
            api_base: Optional API base URL (for local models or custom endpoints)
            temperature: Sampling temperature (default: 0.7)
            max_tokens: Maximum tokens in response (default: 50)
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Set API key if provided
        if api_key:
            self._set_api_key(api_key, api_provider, model)
        
        # Set API base if provided (useful for local models or custom endpoints)
        if api_base:
            if model.startswith("ollama"):
                os.environ["OLLAMA_API_BASE"] = api_base
            else:
                # For other providers, use OPENAI_API_BASE (LiteLLM supports this)
                os.environ["OPENAI_API_BASE"] = api_base
        
        # Configure LiteLLM
        litellm.set_verbose = False  # Set to True for debugging
    
    def _set_api_key(self, api_key: str, api_provider: str | None, model: str) -> None:
        """Set API key in appropriate environment variable based on provider or model."""
        # Determine provider from api_provider parameter or model name
        provider = api_provider
        if not provider:
            if model.startswith("gpt") or model.startswith("azure/"):
                provider = "openai"
            elif model.startswith("claude"):
                provider = "anthropic"
            elif model.startswith("gemini"):
                provider = "gemini"
            elif model.startswith("ollama"):
                provider = "ollama"  # Ollama doesn't need API key
        
        # Set the appropriate environment variable
        if provider == "openai":
            os.environ["OPENAI_API_KEY"] = api_key
        elif provider == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = api_key
        elif provider == "gemini" or provider == "google":
            os.environ["GEMINI_API_KEY"] = api_key
        elif provider == "ollama":
            # Ollama doesn't require API key
            pass
        else:
            # Default to OpenAI for backward compatibility
            os.environ["OPENAI_API_KEY"] = api_key
    
    def reason(self, game_state: dict[str, Any], valid_actions: list[str], rules: str = "") -> str:
        """
        Use LiteLLM to reason about the best action given the game state and rules.
        
        Args:
            game_state: Current game state dictionary
            valid_actions: List of valid actions
            rules: Game rules description string
            
        Returns:
            Selected action string
        """
        # Build prompt
        game_name = game_state.get("game", "unknown")
        board = game_state.get("board", [])
        score = game_state.get("score", 0)
        game_over = game_state.get("game_over", False)
        
        # Include rules in prompt if provided
        rules_section = ""
        if rules:
            rules_section = f"\n\nGAME RULES:\n{rules}\n"
        
        prompt = f"""You are playing the game "{game_name}".{rules_section}

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
