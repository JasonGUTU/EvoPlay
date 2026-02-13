"""Main script to run the agent in a loop with command-line argument support."""

from __future__ import annotations

import argparse
import sys
import webbrowser
import time
from agent.agent import Agent
from agent.config import config
from agent.reasoning import Reasoning, LiteLLMReasoning


def create_reasoning(
    method: str,
    model: str | None = None,
    api_key: str | None = None,
    api_provider: str | None = None,
    api_base: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Reasoning:
    """
    Factory function to create reasoning engine based on method name.
    
    Args:
        method: Reasoning method name (e.g., "litellm")
        model: Model name (optional, uses config default if not provided)
        api_key: API key (optional, uses config if not provided)
        api_provider: API provider name (optional)
        api_base: API base URL (optional)
        temperature: Temperature setting (optional, uses config default if not provided)
        max_tokens: Max tokens setting (optional, uses config default if not provided)
    
    Returns:
        Reasoning engine instance
    """
    method_lower = method.lower()
    
    # Get defaults from config
    if model is None:
        model = config.get_model()
    if api_key is None:
        api_key = config.get_api_key(api_provider or config.get_api_provider())
    if api_provider is None:
        api_provider = config.get_api_provider()
    if api_base is None:
        api_base = config.get_api_base()
    if temperature is None:
        temperature = config.get_temperature()
    if max_tokens is None:
        max_tokens = config.get_max_tokens()
    
    if method_lower == "litellm":
        return LiteLLMReasoning(
            model=model,
            api_key=api_key,
            api_provider=api_provider,
            api_base=api_base,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        raise ValueError(
            f"Unknown reasoning method: {method}. "
            f"Available methods: litellm"
        )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="EvoPlay Agent - AI agent for playing games",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default settings
  python agent/main.py

  # Specify reasoning method and model
  python agent/main.py --reasoning litellm --model gpt-4

  # Use different API provider
  python agent/main.py --api-provider anthropic --model claude-3-sonnet-20240229

  # Play different game
  python agent/main.py --game mergefall

  # Auto-open browser for visualization
  python agent/main.py --auto-open-browser

  # Limit steps and set delay
  python agent/main.py --max-steps 100 --delay 0.5
        """
    )
    
    # Reasoning configuration
    parser.add_argument(
        "--reasoning",
        type=str,
        default=config.get_reasoning_method(),
        help=f"Reasoning method to use (default: {config.get_reasoning_method()})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=config.get_model(),
        help=f"Model name (default: {config.get_model()})",
    )
    parser.add_argument(
        "--api-provider",
        type=str,
        default=config.get_api_provider(),
        help=f"API provider: openai, anthropic, gemini, etc. (default: {config.get_api_provider()})",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key (if not provided, will use config or environment variables)",
    )
    parser.add_argument(
        "--api-base",
        type=str,
        default=config.get_api_base(),
        help="API base URL for local models or custom endpoints",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=config.get_temperature(),
        help=f"Temperature for model (default: {config.get_temperature()})",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=config.get_max_tokens(),
        help=f"Maximum tokens in response (default: {config.get_max_tokens()})",
    )
    
    # Game configuration
    parser.add_argument(
        "--game",
        type=str,
        default=config.get_game_name(),
        help=f"Game name to play (default: {config.get_game_name()})",
    )
    parser.add_argument(
        "--backend-url",
        type=str,
        default=config.get_backend_url(),
        help=f"Backend URL (default: {config.get_backend_url()})",
    )
    parser.add_argument(
        "--frontend-url",
        type=str,
        default=config.get_frontend_url(),
        help=f"Frontend URL (default: {config.get_frontend_url()})",
    )
    parser.add_argument(
        "--session-id",
        type=str,
        default=config.get_session_id(),
        help="Session ID (leave empty to auto-generate)",
    )
    
    # Agent behavior
    parser.add_argument(
        "--max-steps",
        type=int,
        default=config.get_max_steps() or 0,
        help="Maximum number of steps (0 for infinite, default: 0)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=config.get_delay(),
        help=f"Delay between steps in seconds (default: {config.get_delay()})",
    )
    parser.add_argument(
        "--auto-open-browser",
        action="store_true",
        default=config.get_auto_open_browser(),
        help="Automatically open browser for visualization",
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the agent."""
    args = parse_args()
    
    # Convert max_steps: 0 means infinite (None)
    max_steps = args.max_steps if args.max_steps > 0 else None
    
    # Initialize reasoning engine
    try:
        reasoning = create_reasoning(
            method=args.reasoning,
            model=args.model,
            api_key=args.api_key,
            api_provider=args.api_provider,
            api_base=args.api_base,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        print(f"Using reasoning method: {args.reasoning}")
        print(f"Using model: {args.model}")
        if args.api_provider:
            print(f"Using API provider: {args.api_provider}")
    except Exception as e:
        print(f"Error initializing reasoning engine: {e}")
        print("\nPlease check your configuration:")
        print("  1. Set API key in .env file or environment variables")
        print("  2. Verify the reasoning method and model name are correct")
        print("\nExample .env file:")
        print("  OPENAI_API_KEY=your-api-key-here")
        print("  MODEL=gpt-3.5-turbo")
        print("  REASONING_METHOD=litellm")
        sys.exit(1)
    
    # Initialize agent
    agent = Agent(
        reasoning=reasoning,
        backend_url=args.backend_url,
        game_name=args.game,
        session_id=args.session_id,
    )
    
    # Get session_id by calling get_state (this will initialize the session)
    if args.auto_open_browser:
        print("\nInitializing session...")
        try:
            state = agent.get_state()
            agent_session_id = agent.session_id
            if agent_session_id:
                # Construct the frontend URL with session_id and game parameters
                frontend_url_with_params = f"{args.frontend_url}?game={args.game}&session_id={agent_session_id}"
                print(f"\n{'='*50}")
                print(f"Opening browser to visualize agent session...")
                print(f"Session ID: {agent_session_id}")
                print(f"Game: {args.game}")
                print(f"URL: {frontend_url_with_params}")
                print(f"{'='*50}\n")
                
                # Wait a moment to ensure backend is ready
                time.sleep(0.5)
                
                # Open browser
                webbrowser.open(frontend_url_with_params)
            else:
                print("Warning: Could not get session_id, browser will not be opened.")
        except Exception as e:
            print(f"Warning: Failed to open browser: {e}")
            print("You can manually open the frontend and use the session_id from the logs.")
    
    # Run the agent loop
    agent.run_loop(max_steps=max_steps, delay=args.delay)


if __name__ == "__main__":
    main()
