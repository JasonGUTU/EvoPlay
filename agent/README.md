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

1. **`Reasoning` (Abstract Base Class)**: Defines the interface for reasoning engines
2. **`LiteLLMReasoning`**: Unified implementation using LiteLLM to support multiple LLM providers
3. **`Agent`**: Main agent class that:
   - Interacts with backend via HTTP requests
   - Uses reasoning engine to decide actions
   - Manages game loop

## Installation

```bash
cd agent
pip install -r requirements.txt
```

## Configuration

Set the following environment variables:

### Model Configuration (LiteLLM)

```bash
# Model identifier (supports multiple providers)
export MODEL='gpt-3.5-turbo'  # See supported models below

# API Key (LiteLLM will use the appropriate provider based on model)
export API_KEY='your-api-key-here'

# Or use provider-specific keys (LiteLLM will auto-detect):
export OPENAI_API_KEY='your-openai-key'      # For OpenAI models
export ANTHROPIC_API_KEY='your-anthropic-key' # For Claude models
export GEMINI_API_KEY='your-gemini-key'      # For Google models

# Optional: API base URL (for local models or custom endpoints)
export API_BASE='http://localhost:11434'  # For Ollama

# Optional: Model parameters
export TEMPERATURE='0.7'
export MAX_TOKENS='50'
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

### Other Configuration

```bash
# Optional: Backend URL (default: http://localhost:5001)
export BACKEND_URL='http://localhost:5001'

# Optional: Game name (default: 2048)
export GAME_NAME='2048'  # or 'mergefall'

# Optional: Session ID (default: auto-generated)
export SESSION_ID='your-session-id'

# Optional: Maximum steps (default: infinite)
export MAX_STEPS=100

# Optional: Delay between steps in seconds (default: 1.0)
export DELAY=1.0
```

### Backward Compatibility

For backward compatibility, the old environment variables still work:
- `GPT_MODEL` → maps to `MODEL`
- `OPENAI_API_KEY` → used if `API_KEY` is not set

## Usage

### Basic Usage

```bash
# Make sure backend is running first
cd ../backend
python app.py

# In another terminal, run the agent
cd ../agent
python main.py
```

### Switching Models

**Using OpenAI:**
```bash
export MODEL='gpt-4'
export OPENAI_API_KEY='your-openai-key'
python main.py
```

**Using Claude:**
```bash
export MODEL='claude-3-sonnet-20240229'
export ANTHROPIC_API_KEY='your-anthropic-key'
python main.py
```

**Using Local Ollama:**
```bash
# First, make sure Ollama is running locally
export MODEL='ollama/llama2'
export API_BASE='http://localhost:11434'  # Ollama default port
python main.py
```

**Using Google Gemini:**
```bash
export MODEL='gemini/gemini-pro'
export GEMINI_API_KEY='your-gemini-key'
python main.py
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

## Extending with Custom Reasoning Engines

To add a new reasoning engine (e.g., Claude, local model), simply implement the `Reasoning` interface:

```python
from agent.reasoning import Reasoning
from typing import Any

class MyCustomReasoning(Reasoning):
    def reason(self, game_state: dict[str, Any], valid_actions: list[str]) -> str:
        # Your reasoning logic here
        # Return one of the valid_actions
        return valid_actions[0]
```

Then use it with the Agent:

```python
from agent.agent import Agent
from my_custom_reasoning import MyCustomReasoning

reasoning = MyCustomReasoning()
agent = Agent(reasoning=reasoning, game_name="2048")
agent.run_loop()
```

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