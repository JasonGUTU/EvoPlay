"""Agent class - handles interaction with backend and uses reasoning engine."""

from __future__ import annotations

import csv
import time
import json
from pathlib import Path
from typing import Any

import requests
from agent.reasoning import Reasoning

# LLM response logs go here (sibling to backend/logs/)
LLM_LOG_DIR = Path(__file__).resolve().parent.parent / "backend" / "llm_logs"


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
        player_name: str | None = None,
    ):
        """
        Initialize the agent.

        Args:
            reasoning: Reasoning engine instance (e.g., GPTReasoning)
            backend_url: Backend API base URL
            game_name: Name of the game to play
            session_id: Optional session ID (will be generated if not provided)
            player_name: Player name for logs (defaults to model name)
        """
        self.reasoning = reasoning
        self.backend_url = backend_url.rstrip("/")
        self.game_name = game_name
        self.session_id = session_id
        self.step_count = 0
        # Setup agent reasoning logging
        self.log_dir = Path("agent_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.agent_log_file = None
        
        # Use model name as player_name if not explicitly provided
        llm = getattr(reasoning, "llm", None)
        default_name = getattr(llm, "model", "llm-agent")
        if llm and not getattr(llm, "no_thinking", True):
            default_name += "-thinking"
        self.player_name = player_name or default_name
        # LLM response log (created lazily after session_id is known)
        self._llm_log_file = None
        self._llm_log_writer = None
    
    def get_state(self) -> dict[str, Any]:
        """
        Get current game state from backend.
        
        Returns:
            Game state dictionary
        """
        # If no session_id, initialize by calling reset first
        # Backend /state endpoint requires session_id, but /reset can generate one
        if not self.session_id:
            self.reset_game()
        
        url = f"{self.backend_url}/api/game/{self.game_name}/state"
        response = requests.get(url, params={"session_id": self.session_id, "player_name": self.player_name})
        response.raise_for_status()
        state = response.json()
        
        # Update session_id if changed
        if "session_id" in state:
            self.session_id = state["session_id"]
        
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
        response = requests.get(url, params={"session_id": self.session_id, "player_name": self.player_name})
        response.raise_for_status()
        data = response.json()
        return data.get("valid_actions", [])
    
    def get_rules(self) -> str:
        """
        Get game rules description from backend.
        
        Returns:
            Game rules description string
        """
        url = f"{self.backend_url}/api/game/{self.game_name}/rules"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("rules", "")
    
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
            params={"move": action, "session_id": self.session_id, "player_name": self.player_name}
        )
        response.raise_for_status()
        state = response.json()

        # Update session_id if changed
        if "session_id" in state:
            self.session_id = state["session_id"]

        # If bot needs to move, wait then trigger bot_move separately
        # This allows the frontend watcher to see the intermediate state
        if state.get("bot_pending"):
            time.sleep(1.0)
            bot_url = f"{self.backend_url}/api/game/{self.game_name}/bot_move"
            bot_response = requests.get(
                bot_url,
                params={"session_id": self.session_id, "player_name": self.player_name}
            )
            bot_response.raise_for_status()
            state = bot_response.json()
            if "session_id" in state:
                self.session_id = state["session_id"]

        return state
    
    def reset_game(self) -> dict[str, Any]:
        """
        Reset the game to initial state and initialize session if needed.
        
        Returns:
            Initial game state dictionary
        """
        url = f"{self.backend_url}/api/game/{self.game_name}/reset"
        params = {"player_name": self.player_name}
        if self.session_id:
            params["session_id"] = self.session_id

        response = requests.get(url, params=params)
        response.raise_for_status()
        state = response.json()
        
        # Store session_id from response (reset endpoint can generate new session)
        if "session_id" in state:
            self.session_id = state["session_id"]
            if not params:  # If we didn't have session_id before
                print(f"Initialized session_id: {self.session_id}")
        
        self.step_count = 0
        return state
    
    # ── LLM response logging ─────────────────────────────────────────

    def _ensure_llm_log(self) -> None:
        """Create LLM response log file (same name as game log, in llm_logs/)."""
        if self._llm_log_writer is not None:
            return
        if not self.session_id:
            return
        game_dir = LLM_LOG_DIR / self.game_name
        game_dir.mkdir(parents=True, exist_ok=True)
        safe_sid = self.session_id.replace("/", "_").replace("\\", "_")
        log_path = game_dir / f"{safe_sid}.csv"
        self._llm_log_file = open(log_path, "w", encoding="utf-8", newline="")
        self._llm_log_writer = csv.writer(self._llm_log_file)
        self._llm_log_writer.writerow(["step", "raw_response", "parsed_action", "fallback", "valid_actions", "input_tokens", "output_tokens"])

    def _write_llm_log(self, step: int) -> None:
        """Write one LLM response entry."""
        self._ensure_llm_log()
        if self._llm_log_writer is None:
            return
        raw = getattr(self.reasoning, "last_raw_response", "")
        action = getattr(self.reasoning, "last_action", "")
        fallback = getattr(self.reasoning, "last_fallback", False)
        valid = getattr(self, "_last_valid_actions", [])
        usage = getattr(self.reasoning, "last_usage", {"input_tokens": 0, "output_tokens": 0})
        self._llm_log_writer.writerow([step, raw, action, fallback, "|".join(valid), usage["input_tokens"], usage["output_tokens"]])
        self._llm_log_file.flush()

    # ── Step logic ────────────────────────────────────────────────────

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
        self._last_valid_actions = valid_actions

        if not valid_actions:
            print("No valid actions available")
            return state

        # Step 3: Get game rules
        rules = self.get_rules()

        # Step 4: Use reasoning engine to decide on action
        action = self.reasoning.reason(state, valid_actions, rules)
        # Log reasoning history
        self._log_reasoning(state, valid_actions, action)
        
        # Step 5: Log LLM response
        self._write_llm_log(self.step_count + 1)

        # Step 6: Apply the action
        print(f"Step {self.step_count + 1}: Choosing action '{action}'")
        new_state = self.apply_action(action)

        self.step_count += 1
        print(f"  Score: {new_state.get('score', 0)}, Game Over: {new_state.get('game_over', False)}")

        return new_state
    
    def _log_reasoning(self, state: dict[str, Any], valid_actions: list[str], chosen_action: str) -> None:
        """Log the state and chosen action for analysis."""
        if not self.session_id:
            return
            
        if self.agent_log_file is None:
            # Initialize log file
            log_path = self.log_dir / f"{self.game_name}_{self.session_id}.jsonl"
            self.agent_log_file = open(log_path, "a", encoding="utf-8")
            
        step_index = self.step_count + 1
        log_entry = {
            "index": step_index,
            "step": step_index,
            "game": self.game_name,
            "session_id": self.session_id,
            "state": state,
            "valid_actions": valid_actions,
            "chosen_action": chosen_action,
            "timestamp": time.time()
        }
        self.agent_log_file.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        self.agent_log_file.flush()

    def run_loop(self, max_steps: int | None = None, delay: float = 1.0, continue_to_level: int | None = None):
        """
        Run the agent in a loop, continuously playing the game.
        
        Args:
            max_steps: Maximum number of steps to take (None for infinite)
            delay: Delay in seconds between steps
            continue_to_level: Continue playing to this level (for games that support next_level)
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
        except RuntimeError as e:
            print(f"\n\nAgent stopped due to error: {e}")
            self._log_error(step + 1, str(e))
            self._notify_error(str(e))
        except Exception as e:
            print(f"\n\nError in agent loop: {e}")
            self._log_error(step + 1, str(e))
            self._notify_error(str(e))
            raise

    def _log_error(self, step: int, error_msg: str) -> None:
        """Write error record to LLM log so it's visible in analysis."""
        self._ensure_llm_log()
        if self._llm_log_writer is not None:
            self._llm_log_writer.writerow([step, f"ERROR: {error_msg}", "", "ERROR", "", 0, 0])
            self._llm_log_file.flush()

    def _notify_error(self, error_msg: str) -> None:
        """Notify backend about agent error so frontend watchers can see it."""
        if not self.session_id:
            return
        try:
            url = f"{self.backend_url}/api/game/{self.game_name}/agent_error"
            requests.post(url, json={"error": error_msg}, params={"session_id": self.session_id})
        except Exception:
            pass  # Best effort
