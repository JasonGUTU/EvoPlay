# Agent Module

This module provides an AI agent that can play games by interacting with the backend API and using a reasoning engine to make decisions. 

**Key Design**:
- **LiteLLM** is used as middleware to provide a unified interface for calling language models
- **LLM Interface** (`llm.py`) abstracts away provider differences - use this to call any model
- **VanillaReasoning** is a simple vanilla iterative reasoning implementation (no complex agent structures)
- Easy to extend with custom reasoning methods

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
│  (Abstract) │  - Easy to swap different reasoning methods
└──────┬──────┘
       │
       └── VanillaReasoning (vanilla iterative LLM reasoning)
           │
           └── LLM Interface (unified via LiteLLM middleware)
               ├── OpenAI (GPT-3.5, GPT-4, etc.)
               ├── Anthropic (Claude)
               ├── Google (Gemini)
               ├── Local models (Ollama, etc.)
               └── Azure OpenAI, HuggingFace, and more...
```

### Key Components

1. **`config.py`**: Centralized configuration management for API keys and settings
2. **`llm.py`**: Unified LLM interface using LiteLLM as middleware - **use this to call language models**
3. **`Reasoning` (Abstract Base Class)**: Defines the interface for reasoning engines
4. **`reasoning/` folder**: Contains different reasoning implementations:
   - `base.py`: Abstract base class - **start here if developing a new reasoning engine**
   - `vanilla_reasoning.py`: Vanilla iterative LLM reasoning (uses unified LLM interface)
   - `__init__.py`: Exports all reasoning classes
   - **Add your custom reasoning engines here**
5. **`Agent`**: Main agent class that:
   - Interacts with backend via HTTP requests
   - Uses reasoning engine to decide actions
   - Manages game loop
6. **`main.py`**: Entry point with command-line argument support - **register new reasoning methods here**

### Directory Structure

```
agent/
├── __init__.py              # Module initialization
├── config.py                # Configuration management
├── llm.py                   # Unified LLM interface (LiteLLM middleware)
├── agent.py                 # Main Agent class
├── main.py                  # Entry point (CLI support)
├── reasoning.py             # Backward compatibility re-export
├── examples.py              # Usage examples
├── requirements.txt         # Python dependencies
├── README.md                # This file
└── reasoning/               # Reasoning engines folder
    ├── __init__.py          # Exports all reasoning classes
    ├── base.py              # Abstract base class (Reasoning)
    ├── vanilla_reasoning.py # Vanilla iterative LLM reasoning
    └── [your_reasoning].py  # Add your custom reasoning here
```

## Installation

```bash
cd agent
pip install -r requirements.txt
```

## Configuration

### Method 1: Using .env File (Recommended for API Keys Only)

Create a `.env` file in the project root directory (same level as `agent/` and `backend/`) to store your API keys:

```bash
# Create .env file in project root
touch .env
# Or use your preferred editor
```

**Important**: `.env` file should **only contain sensitive information** like API keys. All other configuration (model, game, reasoning method, etc.) should be set via command-line arguments.

Example `.env` file (API keys only):
```bash
# API Keys - choose the provider you want to use
OPENAI_API_KEY=your-openai-api-key-here
# ANTHROPIC_API_KEY=your-anthropic-api-key-here
# GEMINI_API_KEY=your-gemini-api-key-here

# Optional: API base URL for local models (e.g., Ollama)
# API_BASE=http://localhost:11434
```

**Note**: Do NOT put game configuration, reasoning method, or agent settings in `.env`. Use command-line arguments instead (see examples below).

### Method 2: Environment Variables (For API Keys Only)

You can also set API keys as environment variables directly:

```bash
# API Keys only
export OPENAI_API_KEY='your-openai-key'
export ANTHROPIC_API_KEY='your-anthropic-key'
export GEMINI_API_KEY='your-gemini-key'
```

**Note**: For all other settings (model, game, reasoning method, etc.), use command-line arguments. Environment variables for non-sensitive settings are supported for backward compatibility but not recommended.

### Using the Unified LLM Interface

The `llm.py` module provides a unified interface for calling language models through LiteLLM middleware. This allows you to call any supported model without worrying about provider-specific differences.

**Basic Usage**:
```python
from agent.llm import LLM

# Initialize LLM interface
llm = LLM(
    model="gpt-4",
    api_key="your-api-key",  # Optional if set in .env
    temperature=0.7,
    max_tokens=1000
)

# Simple call with a prompt
response = llm.simple_call("What is 2+2?")
print(response)

# Advanced call with message history
response = llm.call(
    messages=[
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "What's the weather?"}
    ],
    system_message="You are a helpful assistant."
)
```

**Key Benefits**:
- Unified API regardless of provider (OpenAI, Anthropic, Google, etc.)
- Automatic provider detection from model name
- No need to handle provider-specific differences
- Easy to switch models without changing code

### Supported Models

LiteLLM supports many models. Here are commonly used models:

**⚠️ Important**: Model availability changes frequently. **Please check [OpenAI's official model documentation](https://platform.openai.com/docs/models) for the latest available models.**

**OpenAI (Recommended):**
- `gpt-4o-mini` - Fast and cost-effective model (default)
- `gpt-4-turbo` - High-performance reasoning model
- `gpt-4` - Standard GPT-4 model
- `o1-preview` / `o1-mini` - OpenAI's reasoning models (if available)
- **Note**: Check [OpenAI Models](https://platform.openai.com/docs/models) for current availability

**Anthropic (Claude):**
- `claude-3-5-sonnet-20241022` - Latest Claude model (recommended)
- `claude-3-opus-20240229` - Most capable Claude model
- `claude-3-sonnet-20240229` - Balanced performance
- `claude-3-haiku-20240307` - Fastest and cheapest

**Google:**
- `gemini/gemini-pro` - Google's Gemini Pro model
- `gemini/gemini-pro-vision` - With vision capabilities
- `gemini/gemini-1.5-pro` - Latest Gemini model

**Local Models (Ollama):**
- `ollama/llama2` - Meta's Llama 2
- `ollama/llama3` - Meta's Llama 3
- `ollama/mistral` - Mistral model
- `ollama/codellama` - Code-focused model

**Azure OpenAI:**
- `azure/gpt-4` - GPT-4 via Azure
- `azure/gpt-4-turbo` - GPT-4 Turbo via Azure

**Other Providers:**
- See [LiteLLM documentation](https://docs.litellm.ai/docs/providers) for the complete list

**How to Check Available Models:**
```bash
# Check OpenAI models via API (requires API key)
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | grep '"id"'

# Or visit OpenAI's official documentation:
# https://platform.openai.com/docs/models
```

### Configuration Priority

Configuration is loaded in the following order (highest priority first):
1. **Command-line arguments** (recommended for all non-sensitive settings)
2. Environment variables
3. `.env` file (recommended for API keys only)
4. Default values

**Best Practice**: 
- Put **API keys** in `.env` file (sensitive information)
- Use **command-line arguments** for everything else (model, game, reasoning method, etc.)

## Usage

### Quick Start

**Complete Startup Sequence** (3 terminals required):

**Step 1: Configure API Key**

Create a `.env` file in the project root (same level as `agent/` and `backend/`):
```bash
# Create .env file
touch .env

# Edit .env and add your API key
# OPENAI_API_KEY=your-api-key-here
```

**Important**: Only put API keys in `.env`. All other settings use command-line arguments.

**Step 2: Start Backend** (Terminal 1)
```bash
cd backend
python app.py
```
Backend will run on `http://localhost:5001`

**Step 3: Start Frontend** (Terminal 2)
```bash
cd frontend
npm install  # Only needed first time
npm run dev
```
Frontend will run on `http://localhost:3000`

**Step 4: Run Agent** (Terminal 3)
```bash
cd agent
python main.py
```

**That's it!** The agent will start playing the game, and you can watch it in the browser at `http://localhost:3000`

**Optional**: Use `--auto-open-browser` to automatically open the frontend:
```bash
python main.py --auto-open-browser
```

### Quick Test

**Minimal test (5 steps)** - You need 3 terminals:

```bash
# Terminal 1: Start backend
cd backend
python app.py

# Terminal 2: Start frontend (optional, for visualization)
cd frontend
npm run dev

# Terminal 3: Run agent for 5 steps
cd agent
python main.py --max-steps 5 --delay 0.5
```

**Note**: Frontend is optional but recommended for visualization. If you don't start the frontend, the agent will still work, but you won't be able to see the game in the browser.

**Test with specific model**:
```bash
python main.py --model gpt-4o-mini --max-steps 10
# Or try other models (check availability first):
python main.py --model gpt-4-turbo --max-steps 10
```

**Test with auto-open browser**:
```bash
python main.py --max-steps 10 --auto-open-browser
```

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
# Use default settings (API key from .env, defaults for everything else)
python main.py

# Specify model and reasoning method
python main.py --reasoning vanilla --model gpt-4

# Use different API provider (API key should be in .env)
python main.py --api-provider anthropic --model claude-3-sonnet-20240229

# Play different game
python main.py --game mergefall

# Auto-open browser for visualization
python main.py --auto-open-browser

# Limit steps and set delay
python main.py --max-steps 100 --delay 0.5

# Full example with all options (API key from .env)
python main.py \
    --reasoning vanilla \
    --model gpt-4 \
    --api-provider openai \
    --temperature 0.8 \
    --max-tokens 100 \
    --game 2048 \
    --max-steps 50 \
    --delay 0.5 \
    --auto-open-browser

# Override API key via command line (if not in .env)
python main.py --api-key your-api-key-here --model gpt-4
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
from agent.reasoning import VanillaReasoning

# Initialize reasoning engine with any supported model
reasoning = VanillaReasoning(
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

**Backward Compatibility**: Old class names still work:
```python
from agent.reasoning import LiteLLMReasoning  # Alias for VanillaReasoning
from agent.reasoning import GPTReasoning      # Alias for VanillaReasoning
```

## How It Works

1. **Get State**: Agent fetches current game state from backend
2. **Get Valid Actions**: Agent gets list of valid actions
3. **Get Rules**: Agent fetches game rules from backend
4. **Reason**: Agent uses reasoning engine to decide on best action
   - VanillaReasoning: Simple iterative process - build prompt, call LLM via unified interface, return action
5. **Apply Action**: Agent sends action to backend
6. **Repeat**: Steps 1-5 are repeated until game over or max steps reached

**VanillaReasoning** is a vanilla iterative reasoning implementation:
- No complex agent structures
- Simple: prompt → LLM call → action
- Uses unified LLM interface (via LiteLLM middleware) to support any model provider

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