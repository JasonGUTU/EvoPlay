"""Main script to run the agent in a loop with command-line argument support."""

from __future__ import annotations

import argparse
import sys
import webbrowser
import time
from pathlib import Path

# Add parent directory to path so we can import agent module
# This allows running from both project root and agent/ directory
_agent_dir = Path(__file__).resolve().parent
_project_root = _agent_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from agent.agent import Agent
from agent.config import config
from agent.reasoning import Reasoning, VanillaReasoning


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
    
    if method_lower == "litellm" or method_lower == "vanilla":
        return VanillaReasoning(
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
            f"Available methods: vanilla (or litellm for backward compatibility)"
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
        help=f"Reasoning method to use: vanilla (default: {config.get_reasoning_method()})",
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
        
        # Debug: Check if MODEL env var is set (should not be in .env)
        import os
        if os.getenv("MODEL"):
            print(f"\n⚠️  Warning: MODEL environment variable is set to: {os.getenv('MODEL')}")
            print("   This will override the default. Consider unsetting it:")
            print("   unset MODEL")
            print("   Or use --model argument to override.")
    except Exception as e:
        print(f"Error initializing reasoning engine: {e}")
        print("\nPlease check your configuration:")
        print("  1. Set API key in .env file or use --api-key argument")
        print("  2. Verify the reasoning method and model name are correct")
        print("\nExample .env file (API keys only):")
        print("  OPENAI_API_KEY=your-api-key-here")
        print("\nUse command-line arguments for other settings:")
        print("  python main.py --model gpt-4 --game 2048 --reasoning litellm")
        sys.exit(1)
    
    # Initialize agent
    agent = Agent(
        reasoning=reasoning,
        backend_url=args.backend_url,
        game_name=args.game,
        session_id=args.session_id,
    )
    
    # Initialize session by calling reset (this will create a new game session)
    if args.auto_open_browser:
        print("\nInitializing session...")
        try:
            state = agent.reset_game()  # Use reset_game to initialize session
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
