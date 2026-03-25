"""Vanilla iterative reasoning - simplest LLM reasoning implementation.

This is a straightforward iterative reasoning process:
1. Receive game state and rules
2. Build a prompt
3. Call language model via unified LLM interface
4. Return the action

No complex agent structures, just simple prompt → LLM → action.
"""

from __future__ import annotations

from typing import Any

from agent.llm import LLM
from .base import Reasoning


class VanillaReasoning(Reasoning):
    """
    Simple vanilla iterative reasoning.
    
    Process:
    1. Build prompt from game state + rules + valid actions
    2. Call LLM via unified interface
    3. Return action
    
    That's it. No agent structures, no complex logic.
    """
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",  # Default model (check OpenAI docs for latest)
        api_key: str | None = None,
        api_provider: str | None = None,
        api_base: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 50,
    ):
        """
        Initialize vanilla reasoning.
        
        Args:
            model: Model name (e.g., "gpt-4", "claude-3-sonnet-20240229")
            api_key: API key (optional, reads from .env if not provided)
            api_provider: Provider name (openai, anthropic, etc.) - auto-detected if None
            api_base: API base URL (for local models like Ollama)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Max tokens in response
        """
        # Initialize unified LLM interface
        self.llm = LLM(
            model=model,
            api_key=api_key,
            api_provider=api_provider,
            api_base=api_base,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    def reason(self, game_state: dict[str, Any], valid_actions: list[str], rules: str = "") -> str:
        """
        Vanilla iterative reasoning: prompt → LLM → action.
        
        Args:
            game_state: Current game state (board, score, etc.)
            valid_actions: List of valid actions (e.g., ["up", "down", "left", "right"])
            rules: Game rules text
            
        Returns:
            Action string (one of valid_actions)
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
        
        # Build game-specific extra context
        extra_context = ""
        if game_name == "mergefall":
            next_tile = game_state.get("next_tile", "?")
            extra_context = f"\nNext tile to drop: {next_tile}\n"

        actions_str = ', '.join(valid_actions)
        prompt = f"""You are playing the game "{game_name}".{rules_section}

Current board:
{self._format_board(board)}
Score: {score}
{extra_context}
IMPORTANT: You MUST choose exactly one action from this list (copy it exactly):
[{actions_str}]

Pick the best action. Respond with ONLY the action string, nothing else."""

        try:
            # Call language model via unified interface
            system_message = "You are a game-playing AI agent. Respond with only the action string."
            response = self.llm.simple_call(prompt, system_message=system_message)

            raw_response = response.strip()
            action = raw_response
            fallback = False

            # Validate that the action is in valid_actions
            if action not in valid_actions:
                # If model returned an invalid action, fallback to first valid action
                print(f"Warning: Model returned invalid action '{action}', using first valid action instead")
                action = valid_actions[0] if valid_actions else ""
                fallback = True

            # Store last response details for logging
            self.last_raw_response = raw_response
            self.last_action = action
            self.last_fallback = fallback

            return action

        except Exception as e:
            print(f"Error calling model ({self.llm.model}): {e}")
            self.last_raw_response = f"ERROR: {e}"
            self.last_action = valid_actions[0] if valid_actions else ""
            self.last_fallback = True
            return self.last_action
    
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
