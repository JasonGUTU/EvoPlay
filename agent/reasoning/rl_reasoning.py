import os
import sys
import numpy as np
from typing import Any

# Ensure EvoPlay is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from .base import Reasoning

class RLReasoning(Reasoning):
    """
    RL Baseline reasoning engine.
    Uses a pre-trained MaskablePPO model to make decisions instead of an LLM.
    """
    
    def __init__(self, model_path: str = None, game_name: str = "tictactoe"):
        try:
            from sb3_contrib.ppo_mask import MaskablePPO
        except ImportError:
            raise ImportError("Please install stable-baselines3 and sb3-contrib to use RLReasoning: pip install stable-baselines3 sb3-contrib")
        
        self.game_name = game_name
        
        # Fallback to default trained model if model_path is None or looks like an LLM model name
        if not model_path or not model_path.endswith(".zip"):
            # 优先尝试加载 medium 模型，如果没有则尝试加载 easy 模型
            medium_model = f"../../../rl/checkpoints/{self.game_name}_medium_klent_ppo.zip"
            easy_model = f"../../../rl/checkpoints/{self.game_name}_easy_klent_ppo.zip"
            
            medium_path = os.path.join(os.path.dirname(__file__), medium_model)
            easy_path = os.path.join(os.path.dirname(__file__), easy_model)
            
            if os.path.exists(medium_path):
                model_path = medium_path
            else:
                model_path = easy_path
            
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"RL Model not found at {model_path}. Please train it first using EvoPlay/rl/train_{self.game_name}.py.")
            
        self.model = MaskablePPO.load(model_path)

    def reason(self, game_state: dict[str, Any], valid_actions: list[str], rules: str = "") -> str:
        if self.game_name == "tictactoe":
            return self._reason_tictactoe(game_state, valid_actions)
        elif self.game_name == "fourinarow":
            return self._reason_fourinarow(game_state, valid_actions)
        elif self.game_name == "othello6":
            return self._reason_othello6(game_state, valid_actions)
        elif self.game_name == "circlecat":
            return self._reason_circlecat(game_state, valid_actions)
        else:
            raise NotImplementedError(f"RL reasoning not implemented for game: {self.game_name}")
            
    def _reason_tictactoe(self, game_state: dict[str, Any], valid_actions: list[str]) -> str:
        board = game_state.get("board", [])
        
        # 1. Prepare observation (3x3 array)
        obs = np.array(board, dtype=np.int8)
        
        # 2. Build action mask (length 9)
        mask = np.zeros(9, dtype=np.int8)
        for r in range(3):
            for c in range(3):
                if board[r][c] == 0:  # EMPTY
                    action_idx = r * 3 + c
                    mask[action_idx] = 1
                    
        # 3. Predict action using the trained model
        # sb3 model.predict supports un-batched observations and returns an un-batched action.
        action, _states = self.model.predict(obs, action_masks=mask, deterministic=True)
        
        # 4. Convert action integer back to string
        if isinstance(action, np.ndarray) and action.size == 1:
            action_int = int(action.item())
        else:
            action_int = int(action)
            
        row = action_int // 3
        col = action_int % 3
        action_str = f"{row} {col}"
        
        # Safety fallback (just in case the mask fails to prevent an invalid move)
        if action_str not in valid_actions and valid_actions:
            import random
            print(f"[RLReasoning Warning] Model predicted invalid action {action_str}, falling back to random.")
            return random.choice(valid_actions)
            
        return action_str

    def _reason_fourinarow(self, game_state: dict[str, Any], valid_actions: list[str]) -> str:
        board = game_state.get("board", [])
        
        # 1. Prepare observation (6x7 array)
        obs = np.array(board, dtype=np.int8)
        
        # 2. Build action mask (length 7)
        mask = np.zeros(7, dtype=np.int8)
        for c in range(7):
            if board[0][c] == 0:  # EMPTY at the top row means column is valid
                mask[c] = 1
                
        # 3. Predict action using the trained model
        action, _states = self.model.predict(obs, action_masks=mask, deterministic=True)
        
        # 4. Convert action integer back to string
        if isinstance(action, np.ndarray) and action.size == 1:
            action_int = int(action.item())
        else:
            action_int = int(action)
            
        action_str = str(action_int)
        
        # Safety fallback
        if action_str not in valid_actions and valid_actions:
            import random
            print(f"[RLReasoning Warning] Model predicted invalid action {action_str}, falling back to random.")
            return random.choice(valid_actions)
            
        return action_str

    def _reason_circlecat(self, game_state: dict[str, Any], valid_actions: list[str]) -> str:
        board = game_state.get("board", [])
        
        # 1. Prepare observation (11x11 array)
        obs = np.zeros((11, 11), dtype=np.int8)
        for i in range(11):
            if i < len(board):
                for j in range(11):
                    if j < len(board[i]):
                        if board[i][j] == "1":
                            obs[i][j] = 1
                        elif board[i][j] == "C":
                            obs[i][j] = 2
                            
        # 2. Build action mask (length 121)
        mask = np.zeros(121, dtype=np.int8)
        for action_str in valid_actions:
            try:
                parts = action_str.split()
                r, c = int(parts[0]), int(parts[1])
                action_idx = r * 11 + c
                mask[action_idx] = 1
            except (ValueError, IndexError):
                pass
                
        if not valid_actions:
            mask[0] = 1  # Fallback to prevent crash if no valid actions
            
        # 3. Predict action
        action, _states = self.model.predict(obs, action_masks=mask, deterministic=True)
        
        # 4. Convert action back to string
        if isinstance(action, np.ndarray) and action.size == 1:
            action_int = int(action.item())
        else:
            action_int = int(action)
            
        row = action_int // 11
        col = action_int % 11
        action_str = f"{row} {col}"
        
        if action_str not in valid_actions and valid_actions:
            import random
            print(f"[RLReasoning Warning] Model predicted invalid action {action_str}, falling back to random.")
            return random.choice(valid_actions)
            
        return action_str

    def _reason_othello6(self, game_state: dict[str, Any], valid_actions: list[str]) -> str:
        board = game_state.get("board", [])
        
        # 1. Prepare observation (6x6 array)
        obs = np.array(board, dtype=np.int8)
        
        # 2. Build action mask (length 36)
        mask = np.zeros(36, dtype=np.int8)
        
        if not valid_actions or (len(valid_actions) == 1 and valid_actions[0] == "pass"):
            # Model needs to output 0 for 'pass'
            mask[0] = 1
        else:
            for action_str in valid_actions:
                if action_str == "pass":
                    continue
                try:
                    parts = action_str.split()
                    r, c = int(parts[0]), int(parts[1])
                    action_idx = r * 6 + c
                    mask[action_idx] = 1
                except (ValueError, IndexError):
                    pass
                    
        # 3. Predict action using the trained model
        action, _states = self.model.predict(obs, action_masks=mask, deterministic=True)
        
        # 4. Convert action integer back to string
        if isinstance(action, np.ndarray) and action.size == 1:
            action_int = int(action.item())
        else:
            action_int = int(action)
            
        if not valid_actions or (len(valid_actions) == 1 and valid_actions[0] == "pass"):
            action_str = "pass"
        else:
            row = action_int // 6
            col = action_int % 6
            action_str = f"{row} {col}"
            
        # Safety fallback
        if action_str not in valid_actions and valid_actions:
            import random
            print(f"[RLReasoning Warning] Model predicted invalid action {action_str}, falling back to random.")
            return random.choice(valid_actions)
            
        return action_str
