"""Agent class - handles interaction with backend and uses reasoning engine."""

from __future__ import annotations

import time
import requests
from typing import Any
from .reasoning import Reasoning


class Agent:
    """
    Agent that interacts with the game backend and uses a reasoning engine
    to decide on actions.
    
    Architecture:
    - Reasoning (language model) is decoupled from operations (backend interaction)
    - Easy to swap different reasoning engines without changing Agent logic
    """
    
    def __init__(
        self,
        reasoning: Reasoning,
        backend_url: str = "http://localhost:5001",
        game_name: str = "2048",
        session_id: str | None = None,
    ):
        """
        Initialize the agent.
        
        Args:
            reasoning: Reasoning engine instance (e.g., GPTReasoning)
            backend_url: Backend API base URL
            game_name: Name of the game to play
            session_id: Optional session ID (will be generated if not provided)
        """
        self.reasoning = reasoning
        self.backend_url = backend_url.rstrip("/")
        self.game_name = game_name
        self.session_id = session_id
        self.step_count = 0
    
    def get_state(self) -> dict[str, Any]:
        """
        Get current game state from backend.
        
        Returns:
            Game state dictionary
        """
        if not self.session_id:
            # First call - get state to initialize session
            url = f"{self.backend_url}/api/game/{self.game_name}/state"
            # Backend will generate session_id if not provided
            response = requests.get(url, params={"session_id": ""})
        else:
            url = f"{self.backend_url}/api/game/{self.game_name}/state"
            response = requests.get(url, params={"session_id": self.session_id})
        
        response.raise_for_status()
        state = response.json()
        
        # Store session_id from response if we don't have one
        if not self.session_id and "session_id" in state:
            self.session_id = state["session_id"]
            print(f"Initialized session_id: {self.session_id}")
        
        return state
    
    def get_valid_actions(self) -> list[str]:
        """
        Get list of valid actions from backend.
        
        Returns:
            List of valid action strings
        """
        if not self.session_id:
            # Need to get state first to initialize session
            self.get_state()
        
        url = f"{self.backend_url}/api/game/{self.game_name}/valid_actions"
        response = requests.get(url, params={"session_id": self.session_id})
        response.raise_for_status()
        data = response.json()
        return data.get("valid_actions", [])
    
    def apply_action(self, action: str) -> dict[str, Any]:
        """
        Apply an action to the game via backend.
        
        Args:
            action: Action string to execute
            
        Returns:
            Updated game state dictionary
        """
        if not self.session_id:
            # Initialize session first
            self.get_state()
        
        url = f"{self.backend_url}/api/game/{self.game_name}/action"
        response = requests.get(
            url,
            params={"move": action, "session_id": self.session_id}
        )
        response.raise_for_status()
        state = response.json()
        
        # Update session_id if changed
        if "session_id" in state:
            self.session_id = state["session_id"]
        
        return state
    
    def reset_game(self) -> dict[str, Any]:
        """
        Reset the game to initial state.
        
        Returns:
            Initial game state dictionary
        """
        url = f"{self.backend_url}/api/game/{self.game_name}/reset"
        params = {}
        if self.session_id:
            params["session_id"] = self.session_id
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        state = response.json()
        
        # Update session_id
        if "session_id" in state:
            self.session_id = state["session_id"]
        
        self.step_count = 0
        return state
    
    def step(self) -> dict[str, Any]:
        """
        Execute one step: get state, reason about action, apply action.
        
        Returns:
            Updated game state after action
        """
        # Step 1: Get current state
        state = self.get_state()
        
        # Check if game is over
        if state.get("game_over", False):
            print(f"Game over! Final score: {state.get('score', 0)}")
            return state
        
        # Step 2: Get valid actions
        valid_actions = self.get_valid_actions()
        
        if not valid_actions:
            print("No valid actions available")
            return state
        
        # Step 3: Use reasoning engine to decide on action
        action = self.reasoning.reason(state, valid_actions)
        
        # Step 4: Apply the action
        print(f"Step {self.step_count + 1}: Choosing action '{action}'")
        new_state = self.apply_action(action)
        
        self.step_count += 1
        print(f"  Score: {new_state.get('score', 0)}, Game Over: {new_state.get('game_over', False)}")
        
        return new_state
    
    def run_loop(self, max_steps: int | None = None, delay: float = 1.0):
        """
        Run the agent in a loop, continuously playing the game.
        
        Args:
            max_steps: Maximum number of steps to take (None for infinite)
            delay: Delay in seconds between steps
        """
        print(f"Starting agent loop for game '{self.game_name}'")
        print(f"Backend URL: {self.backend_url}")
        print(f"Reasoning engine: {type(self.reasoning).__name__}")
        print("-" * 50)
        
        step = 0
        try:
            while max_steps is None or step < max_steps:
                state = self.step()
                
                if state.get("game_over", False):
                    print("\n" + "=" * 50)
                    print("Game finished!")
                    print(f"Final score: {state.get('score', 0)}")
                    print(f"Total steps: {self.step_count}")
                    print("=" * 50)
                    break
                
                step += 1
                
                # Delay between steps
                if delay > 0:
                    time.sleep(delay)
        
        except KeyboardInterrupt:
            print("\n\nAgent loop interrupted by user")
        except Exception as e:
            print(f"\n\nError in agent loop: {e}")
            raise
