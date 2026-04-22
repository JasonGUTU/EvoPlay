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
from agent.reasoning import Reasoning, VanillaReasoning, RLReasoning


def create_reasoning(
    method: str,
    model: str | None = None,
    api_key: str | None = None,
    api_provider: str | None = None,
    api_base: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    no_thinking: bool = False,
    extra_headers: dict | None = None,
    use_cot: bool = False,
    game_name: str = "tictactoe",
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
            no_thinking=no_thinking,
            extra_headers=extra_headers,
            use_cot=use_cot,
        )
    elif method_lower == "rl":
        return RLReasoning(
            model_path=model,  # Reusing model arg for model_path, if provided
            game_name=game_name,
        )
    else:
        raise ValueError(
            f"Unknown reasoning method: {method}. "
            f"Available methods: vanilla, rl (or litellm for backward compatibility)"
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
    parser.add_argument(
        "--difficulty",
        type=str,
        default=None,
        help="Difficulty level for bot games (easy, medium, hard)",
    )
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        default=False,
        help="Disable thinking/reasoning mode for models that support it (e.g., Qwen3.5)",
    )
    parser.add_argument(
        "--use-cot",
        action="store_true",
        default=False,
        help="Enable explicit Chain-of-Thought style prompting in the reasoning layer",
    )
    parser.add_argument(
        "--extra-headers",
        type=str,
        default=None,
        help='Extra HTTP headers as JSON string (e.g., \'{"cf-aig-metadata": "..."}\')',
    )
    parser.add_argument(
        "--continue-to-level",
        type=int,
        default=None,
        help="Continue to the specified level in a single agent process when the game supports next_level",
    )

    return parser.parse_args()


def main():
    """Main entry point for the agent."""
    args = parse_args()
    
    # Convert max_steps: 0 means infinite (None)
    max_steps = args.max_steps if args.max_steps > 0 else None
    
    # Initialize reasoning engine
    try:
        import json as _json
        extra_headers = _json.loads(args.extra_headers) if args.extra_headers else None
        reasoning = create_reasoning(
            method=args.reasoning,
            model=args.model,
            api_key=args.api_key,
            api_provider=args.api_provider,
            api_base=args.api_base,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            no_thinking=args.no_thinking,
            extra_headers=extra_headers,
            use_cot=args.use_cot,
            game_name=args.game,
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

    # Always reset to initialize session (and set difficulty if provided)
    print("\nInitializing session...")
    import requests as _req
    reset_params = {}
    if agent.session_id:
        reset_params["session_id"] = agent.session_id
    reset_params["player_name"] = agent.player_name
    if args.difficulty:
        reset_params["difficulty"] = args.difficulty
    reset_url = f"{args.backend_url}/api/game/{args.game}/reset"
    _reset_res = _req.get(reset_url, params=reset_params)
    _reset_state = _reset_res.json()
    if "session_id" in _reset_state:
        agent.session_id = _reset_state["session_id"]
    agent.step_count = 0

    # Print watch URL
    watch_url = f"{args.frontend_url}?game={args.game}&session_id={agent.session_id}"
    print(f"\n{'='*60}")
    print(f"  Game:       {args.game}")
    print(f"  Model:      {args.model}")
    print(f"  Difficulty: {args.difficulty or 'default'}")
    print(f"  Session:    {agent.session_id}")
    print(f"  Watch URL:  {watch_url}")
    print(f"{'='*60}\n")

    if args.auto_open_browser:
        try:
            time.sleep(0.5)
            webbrowser.open(watch_url)
        except Exception as e:
            print(f"Warning: Failed to open browser: {e}")
    
    # Run the agent loop
    agent.run_loop(max_steps=max_steps, delay=args.delay, continue_to_level=args.continue_to_level)


if __name__ == "__main__":
    main()
