# Agent Module

This module provides an AI agent that can play games by interacting with the backend API and using a reasoning engine to make decisions. The agent uses **LiteLLM** as a unified interface to support multiple LLM providers, making it easy to switch between different models.

## Architecture

The agent is designed with a decoupled architecture:

```
┌─────────────┐
│   Agent     │  Main agent class that orchestrates the game loop
│             │  - Handles backend API interactions
│             │  - Manages game state and actions
└──────┬──────┘
       │ uses
       ▼
┌─────────────┐
│  Reasoning  │  Abstract interface for reasoning engines
│  (Abstract) │  - Easy to swap different models
└──────┬──────┘
       │
       └── LiteLLMReasoning (unified interface via LiteLLM)
           ├── OpenAI (GPT-3.5, GPT-4, etc.)
           ├── Anthropic (Claude)
           ├── Google (Gemini)
           ├── Local models (Ollama, etc.)
           └── Azure OpenAI, HuggingFace, and more...
```

### Key Components

1. **`config.py`**: Centralized configuration management for API keys and settings
2. **`Reasoning` (Abstract Base Class)**: Defines the interface for reasoning engines
3. **`reasoning/` folder**: Contains different reasoning implementations:
   - `base.py`: Abstract base class - **start here if developing a new reasoning engine**
   - `litellm_reasoning.py`: LiteLLM-based implementation
   - `__init__.py`: Exports all reasoning classes
   - **Add your custom reasoning engines here**
4. **`Agent`**: Main agent class that:
   - Interacts with backend via HTTP requests
   - Uses reasoning engine to decide actions
   - Manages game loop
5. **`main.py`**: Entry point with command-line argument support - **register new reasoning methods here**

### Directory Structure

```
agent/
├── __init__.py              # Module initialization
├── config.py                # Configuration management
├── agent.py                 # Main Agent class
├── main.py                  # Entry point (CLI support)
├── reasoning.py             # Backward compatibility re-export
├── examples.py              # Usage examples
├── requirements.txt         # Python dependencies
├── README.md                # This file
└── reasoning/               # Reasoning engines folder
    ├── __init__.py          # Exports all reasoning classes
    ├── base.py              # Abstract base class (Reasoning)
    ├── litellm_reasoning.py # LiteLLM implementation
    └── [your_reasoning].py  # Add your custom reasoning here
```

## Installation

```bash
cd agent
pip install -r requirements.txt
```

## Configuration

### Method 1: Using .env File (Recommended)

Create a `.env` file in the project root directory (same level as `agent/` and `backend/`):

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API keys
```

Example `.env` file:
```bash
# API Keys (choose the provider you want to use)
OPENAI_API_KEY=your-openai-api-key-here
# ANTHROPIC_API_KEY=your-anthropic-api-key-here
# GEMINI_API_KEY=your-gemini-api-key-here

# Model Configuration
MODEL=gpt-3.5-turbo
API_PROVIDER=openai
API_BASE=

# Reasoning Method
REASONING_METHOD=litellm

# Game Configuration
GAME_NAME=2048
BACKEND_URL=http://localhost:5001
FRONTEND_URL=http://localhost:3000

# Agent Settings
TEMPERATURE=0.7
MAX_TOKENS=50
MAX_STEPS=0
DELAY=1.0
AUTO_OPEN_BROWSER=false
```

### Method 2: Environment Variables

You can also set environment variables directly:

```bash
# API Keys
export OPENAI_API_KEY='your-openai-key'
export ANTHROPIC_API_KEY='your-anthropic-key'
export GEMINI_API_KEY='your-gemini-key'

# Model Configuration
export MODEL='gpt-3.5-turbo'
export API_PROVIDER='openai'
export API_BASE=''  # For local models like Ollama

# Reasoning Method
export REASONING_METHOD='litellm'

# Game Configuration
export GAME_NAME='2048'
export BACKEND_URL='http://localhost:5001'
export FRONTEND_URL='http://localhost:3000'

# Agent Settings
export TEMPERATURE='0.7'
export MAX_TOKENS='50'
export MAX_STEPS='0'  # 0 means infinite
export DELAY='1.0'
export AUTO_OPEN_BROWSER='false'
```

### Supported Models

LiteLLM supports many models. Here are some examples:

**OpenAI:**
- `gpt-3.5-turbo`
- `gpt-4`
- `gpt-4-turbo-preview`

**Anthropic (Claude):**
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307`

**Google:**
- `gemini/gemini-pro`
- `gemini/gemini-pro-vision`

**Local Models (Ollama):**
- `ollama/llama2`
- `ollama/mistral`
- `ollama/codellama`

**Azure OpenAI:**
- `azure/gpt-4`
- `azure/gpt-35-turbo`

See [LiteLLM documentation](https://docs.litellm.ai/docs/providers) for the full list.

### Configuration Priority

Configuration is loaded in the following order (highest priority first):
1. Command-line arguments
2. Environment variables
3. `.env` file
4. Default values

## Usage

### Quick Start

**Step 1: Configure API Key**

Create a `.env` file in the project root:
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API key
# OPENAI_API_KEY=your-api-key-here
```

**Step 2: Start Backend**
```bash
cd backend
python app.py
```

**Step 3: Run Agent (in another terminal)**
```bash
cd agent
python main.py
```

That's it! The agent will start playing the game using default settings.

### Basic Usage

```bash
# Make sure backend is running first
cd backend
python app.py

# In another terminal, run the agent
cd agent
python main.py
```

### Command-Line Arguments

The agent supports comprehensive command-line arguments. Use `--help` to see all options:

```bash
python main.py --help
```

**Common Examples:**

```bash
# Use default settings from .env or environment variables
python main.py

# Specify reasoning method and model
python main.py --reasoning litellm --model gpt-4

# Use different API provider
python main.py --api-provider anthropic --model claude-3-sonnet-20240229

# Play different game
python main.py --game mergefall

# Auto-open browser for visualization
python main.py --auto-open-browser

# Limit steps and set delay
python main.py --max-steps 100 --delay 0.5

# Full example with all options
python main.py \
    --reasoning litellm \
    --model gpt-4 \
    --api-provider openai \
    --api-key your-api-key \
    --temperature 0.8 \
    --max-tokens 100 \
    --game 2048 \
    --max-steps 50 \
    --delay 0.5 \
    --auto-open-browser
```

### Switching Models via Command Line

**Using OpenAI:**
```bash
python main.py --model gpt-4 --api-provider openai
```

**Using Claude:**
```bash
python main.py --model claude-3-sonnet-20240229 --api-provider anthropic
```

**Using Local Ollama:**
```bash
python main.py --model ollama/llama2 --api-base http://localhost:11434
```

**Using Google Gemini:**
```bash
python main.py --model gemini/gemini-pro --api-provider gemini
```

### Programmatic Usage

```python
from agent.agent import Agent
from agent.reasoning import LiteLLMReasoning

# Initialize reasoning engine with any supported model
reasoning = LiteLLMReasoning(
    model="gpt-4",  # or "claude-3-opus-20240229", "ollama/llama2", etc.
    api_key="your-api-key",  # Optional if set via env vars
    temperature=0.7,
    max_tokens=50
)

# Initialize agent
agent = Agent(
    reasoning=reasoning,
    backend_url="http://localhost:5001",
    game_name="2048",
)

# Run for 10 steps
agent.run_loop(max_steps=10, delay=1.0)
```

### Backward Compatibility

The old `GPTReasoning` class is still available as an alias:
```python
from agent.reasoning import GPTReasoning  # Same as LiteLLMReasoning
```

## How It Works

1. **Get State**: Agent fetches current game state from backend
2. **Get Valid Actions**: Agent gets list of valid actions
3. **Reason**: Agent uses reasoning engine (via LiteLLM) to decide on best action
4. **Apply Action**: Agent sends action to backend
5. **Repeat**: Steps 1-4 are repeated until game over or max steps reached

LiteLLM acts as a unified interface, automatically handling the differences between various LLM providers, so you can switch models without changing any code.

## Developing a New Reasoning Engine

This guide will walk you through creating a custom reasoning engine from scratch. A reasoning engine is responsible for deciding which action to take based on the current game state.

### Step-by-Step Guide

#### Step 1: Understand the Interface

All reasoning engines must implement the `Reasoning` abstract base class, which requires one method:

```python
def reason(
    self, 
    game_state: dict[str, Any], 
    valid_actions: list[str], 
    rules: str = ""
) -> str:
    """
    Args:
        game_state: Dictionary containing current game state:
            - "game": Game name (e.g., "2048", "mergefall")
            - "board": Game board (2D list or 1D list)
            - "score": Current score (int)
            - "game_over": Whether game is over (bool)
            - "valid_actions": List of valid actions (list[str])
            - Additional game-specific fields
        
        valid_actions: List of currently valid action strings
            - For 2048: ["up", "down", "left", "right"]
            - For MergeFall: ["drop 0", "drop 1", ..., "drop 4"]
        
        rules: Game rules description string (from backend)
    
    Returns:
        Action string (must be one of valid_actions)
    """
```

#### Step 2: Create Your Reasoning Class

Create a new file in `agent/reasoning/` folder, for example `agent/reasoning/my_custom_reasoning.py`:

```python
"""My custom reasoning engine implementation."""

from __future__ import annotations

from typing import Any
from agent.reasoning.base import Reasoning


class MyCustomReasoning(Reasoning):
    """
    Custom reasoning engine that implements your specific strategy.
    
    This is a template - replace with your actual reasoning logic.
    """
    
    def __init__(
        self,
        param1: str = "default",
        param2: int = 10,
        **kwargs  # Accept additional kwargs for flexibility
    ):
        """
        Initialize your reasoning engine.
        
        Args:
            param1: Example parameter
            param2: Another example parameter
            **kwargs: Additional parameters (will be passed from config/command line)
        """
        self.param1 = param1
        self.param2 = param2
        # Initialize any other resources you need (models, heuristics, etc.)
    
    def reason(
        self, 
        game_state: dict[str, Any], 
        valid_actions: list[str], 
        rules: str = ""
    ) -> str:
        """
        Decide on the best action given the current game state.
        
        This is where your reasoning logic goes. You can:
        - Use the game rules to understand the game
        - Analyze the board state
        - Apply heuristics or algorithms
        - Call external APIs or models
        - Use any other strategy you want
        
        Returns:
            One of the valid_actions
        """
        # Example: Simple random selection (replace with your logic)
        import random
        if not valid_actions:
            return ""
        
        # Your reasoning logic here
        # For example:
        # - Analyze board patterns
        # - Calculate scores for each action
        # - Use machine learning models
        # - Apply game-specific heuristics
        
        # For now, just return a random valid action
        return random.choice(valid_actions)
```

#### Step 3: Register in `reasoning/__init__.py`

Add your new class to the exports in `agent/reasoning/__init__.py`:

```python
"""Reasoning module - different reasoning methods for game agents."""

from __future__ import annotations

from .base import Reasoning
from .litellm_reasoning import LiteLLMReasoning
from .my_custom_reasoning import MyCustomReasoning  # Add this line

# Backward compatibility alias
GPTReasoning = LiteLLMReasoning

__all__ = [
    "Reasoning",
    "LiteLLMReasoning",
    "GPTReasoning",
    "MyCustomReasoning",  # Add this line
]
```

#### Step 4: Add to Factory Function in `main.py`

Update the `create_reasoning()` function in `agent/main.py` to support your new method:

```python
def create_reasoning(
    method: str,
    model: str | None = None,
    api_key: str | None = None,
    # ... other parameters ...
    **kwargs  # Additional kwargs for custom reasoning engines
) -> Reasoning:
    """Factory function to create reasoning engine based on method name."""
    method_lower = method.lower()
    
    # ... existing code for litellm ...
    
    if method_lower == "my_custom":
        # Extract parameters specific to your reasoning engine
        param1 = kwargs.get("param1", "default")
        param2 = kwargs.get("param2", 10)
        
        return MyCustomReasoning(
            param1=param1,
            param2=param2,
            **kwargs
        )
    
    else:
        raise ValueError(
            f"Unknown reasoning method: {method}. "
            f"Available methods: litellm, my_custom"
        )
```

#### Step 5: Add Command-Line Arguments (Optional)

If your reasoning engine needs additional parameters, add them to the argument parser in `main.py`:

```python
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(...)
    
    # ... existing arguments ...
    
    # Add arguments for your custom reasoning engine
    parser.add_argument(
        "--param1",
        type=str,
        default="default",
        help="Parameter 1 for my_custom reasoning",
    )
    parser.add_argument(
        "--param2",
        type=int,
        default=10,
        help="Parameter 2 for my_custom reasoning",
    )
    
    return parser.parse_args()
```

Then pass them to `create_reasoning()`:

```python
def main():
    args = parse_args()
    
    reasoning = create_reasoning(
        method=args.reasoning,
        # ... other parameters ...
        param1=args.param1,  # Add this
        param2=args.param2,  # Add this
    )
```

#### Step 6: Test Your Reasoning Engine

**Option A: Via Command Line**

```bash
# Test with default parameters
python main.py --reasoning my_custom

# Test with custom parameters
python main.py --reasoning my_custom --param1 "custom_value" --param2 20
```

**Option B: Programmatically**

```python
from agent.agent import Agent
from agent.reasoning import MyCustomReasoning

# Create your reasoning engine
reasoning = MyCustomReasoning(
    param1="test",
    param2=15
)

# Use it with an agent
agent = Agent(
    reasoning=reasoning,
    backend_url="http://localhost:5001",
    game_name="2048",
)

# Test for a few steps
agent.run_loop(max_steps=10, delay=1.0)
```

**Option C: Unit Test**

Create a test file `agent/tests/test_my_custom_reasoning.py`:

```python
import unittest
from agent.reasoning import MyCustomReasoning

class TestMyCustomReasoning(unittest.TestCase):
    def setUp(self):
        self.reasoning = MyCustomReasoning()
    
    def test_reason_returns_valid_action(self):
        game_state = {
            "game": "2048",
            "board": [[2, 4, 0, 0], [0, 2, 4, 0], [0, 0, 2, 4], [0, 0, 0, 2]],
            "score": 100,
            "game_over": False,
        }
        valid_actions = ["up", "down", "left", "right"]
        rules = "2048 game rules..."
        
        action = self.reasoning.reason(game_state, valid_actions, rules)
        
        self.assertIn(action, valid_actions)

if __name__ == "__main__":
    unittest.main()
```

### Complete Example: Simple Heuristic Reasoning

Here's a complete example of a simple heuristic-based reasoning engine for 2048:

```python
"""Simple heuristic reasoning for 2048 game."""

from __future__ import annotations

from typing import Any
from agent.reasoning.base import Reasoning


class HeuristicReasoning(Reasoning):
    """
    Simple heuristic-based reasoning for 2048.
    
    Strategy:
    1. Prefer moves that merge tiles
    2. Keep largest tile in a corner
    3. Avoid moves that create gaps
    """
    
    def __init__(self, prefer_corner: str = "bottom-right", **kwargs):
        """
        Args:
            prefer_corner: Which corner to keep largest tile ("top-left", "top-right", 
                          "bottom-left", "bottom-right")
        """
        self.prefer_corner = prefer_corner
    
    def reason(
        self, 
        game_state: dict[str, Any], 
        valid_actions: list[str], 
        rules: str = ""
    ) -> str:
        """Choose action based on simple heuristics."""
        if not valid_actions:
            return ""
        
        board = game_state.get("board", [])
        
        # Simple heuristic: prefer actions that move tiles toward preferred corner
        if self.prefer_corner == "bottom-right":
            # Prefer down and right
            if "down" in valid_actions:
                return "down"
            if "right" in valid_actions:
                return "right"
        
        # Fallback: return first valid action
        return valid_actions[0]
```

### Best Practices

1. **Error Handling**: Always validate inputs and handle edge cases:
   ```python
   def reason(self, game_state, valid_actions, rules=""):
       if not valid_actions:
           return ""  # or raise an exception
       
       # Validate game_state structure
       if "board" not in game_state:
           raise ValueError("Invalid game state: missing 'board'")
   ```

2. **Logging**: Add logging for debugging:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   
   def reason(self, game_state, valid_actions, rules=""):
       logger.debug(f"Choosing action from {valid_actions}")
       action = self._choose_action(game_state, valid_actions)
       logger.info(f"Selected action: {action}")
       return action
   ```

3. **Configuration**: Make your reasoning engine configurable:
   ```python
   def __init__(self, strategy="aggressive", lookahead=2, **kwargs):
       self.strategy = strategy
       self.lookahead = lookahead
   ```

4. **Documentation**: Document your reasoning logic clearly:
   ```python
   """
   This reasoning engine uses a minimax algorithm with alpha-beta pruning
   to look ahead N moves and choose the optimal action.
   """
   ```

5. **Testing**: Write comprehensive tests for different game states and edge cases.

### Advanced: Multi-Step Reasoning

For more sophisticated reasoning engines, you might want to:

1. **Lookahead**: Simulate future moves to evaluate actions
2. **State Evaluation**: Create a function to evaluate game states
3. **Caching**: Cache evaluated states for performance
4. **Parallel Processing**: Evaluate multiple actions in parallel

Example structure:

```python
class AdvancedReasoning(Reasoning):
    def __init__(self, lookahead_depth: int = 3, **kwargs):
        self.lookahead_depth = lookahead_depth
        self.cache = {}  # Cache for state evaluations
    
    def reason(self, game_state, valid_actions, rules=""):
        # Evaluate each action by looking ahead
        best_action = None
        best_score = float('-inf')
        
        for action in valid_actions:
            score = self._evaluate_action(game_state, action, self.lookahead_depth)
            if score > best_score:
                best_score = score
                best_action = action
        
        return best_action
    
    def _evaluate_action(self, state, action, depth):
        # Your evaluation logic here
        # Can use minimax, MCTS, or other algorithms
        pass
```

### Troubleshooting

**Problem**: "Unknown reasoning method" error
- **Solution**: Make sure you've added your method to `create_reasoning()` in `main.py`

**Problem**: Reasoning engine not found
- **Solution**: Check that you've imported and exported it in `reasoning/__init__.py`

**Problem**: Parameters not being passed
- **Solution**: Verify that parameters are passed through `create_reasoning()` and `parse_args()`

**Problem**: Invalid action returned
- **Solution**: Always validate that the returned action is in `valid_actions` list

## API Methods

### Agent Class

- `get_state()`: Get current game state from backend
- `get_valid_actions()`: Get list of valid actions
- `apply_action(action)`: Apply an action to the game
- `reset_game()`: Reset the game to initial state
- `step()`: Execute one step (get state → reason → apply action)
- `run_loop(max_steps, delay)`: Run agent in a continuous loop

## Notes

- The agent automatically handles session management
- If the model returns an invalid action, the agent falls back to the first valid action
- The agent stops automatically when the game is over
- Use Ctrl+C to interrupt the agent loop
- LiteLLM automatically handles API differences between providers
- For local models (Ollama), make sure the model is downloaded and running
- Check [LiteLLM documentation](https://docs.litellm.ai/) for advanced configuration options