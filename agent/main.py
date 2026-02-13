"""Main script to run the agent in a loop."""

from __future__ import annotations

import os
import sys
from agent.agent import Agent
from agent.reasoning import LiteLLMReasoning


def main():
    """Main entry point for the agent."""
    # Configuration
    backend_url = os.getenv("BACKEND_URL", "http://localhost:5001")
    game_name = os.getenv("GAME_NAME", "2048")
    session_id = os.getenv("SESSION_ID", None)
    max_steps = int(os.getenv("MAX_STEPS", "0")) or None  # 0 means infinite
    delay = float(os.getenv("DELAY", "1.0"))
    
    # Model configuration (supports multiple providers via LiteLLM)
    model = os.getenv("MODEL", "gpt-3.5-turbo")
    api_key = os.getenv("API_KEY")  # Generic API key (LiteLLM will use appropriate env var)
    api_base = os.getenv("API_BASE", None)  # For local models or custom endpoints
    temperature = float(os.getenv("TEMPERATURE", "0.7"))
    max_tokens = int(os.getenv("MAX_TOKENS", "50"))
    
    # Backward compatibility: support GPT_MODEL and OPENAI_API_KEY
    if os.getenv("GPT_MODEL"):
        model = os.getenv("GPT_MODEL")
    if os.getenv("OPENAI_API_KEY") and not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    
    # Initialize reasoning engine
    try:
        reasoning = LiteLLMReasoning(
            model=model,
            api_key=api_key,
            api_base=api_base,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        print(f"Using model: {model}")
    except Exception as e:
        print(f"Error initializing reasoning engine: {e}")
        print("\nPlease set the appropriate API key environment variable:")
        print("  For OpenAI: export OPENAI_API_KEY='your-api-key'")
        print("  For Anthropic: export ANTHROPIC_API_KEY='your-api-key'")
        print("  For Google: export GEMINI_API_KEY='your-api-key'")
        print("  For local models (Ollama): no API key needed, set API_BASE if needed")
        sys.exit(1)
    
    # Initialize agent
    agent = Agent(
        reasoning=reasoning,
        backend_url=backend_url,
        game_name=game_name,
        session_id=session_id,
    )
    
    # Run the agent loop
    agent.run_loop(max_steps=max_steps, delay=delay)


if __name__ == "__main__":
    main()
