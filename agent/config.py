"""Configuration management for API keys and agent settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class Config:
    """
    Centralized configuration management for API keys and agent settings.
    
    Supports loading from:
    1. Environment variables (highest priority)
    2. .env file in project root
    3. Default values
    """
    
    # Default values
    DEFAULT_BACKEND_URL = "http://localhost:5001"
    DEFAULT_FRONTEND_URL = "http://localhost:3000"
    DEFAULT_GAME_NAME = "2048"
    DEFAULT_REASONING_METHOD = "litellm"
    DEFAULT_MODEL = "gpt-3.5-turbo"
    DEFAULT_API_PROVIDER = "openai"
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 50
    DEFAULT_MAX_STEPS = 0  # 0 means infinite
    DEFAULT_DELAY = 1.0
    DEFAULT_AUTO_OPEN_BROWSER = False
    
    def __init__(self):
        """Initialize configuration, loading from .env file if present."""
        self._load_env_file()
    
    def _load_env_file(self) -> None:
        """Load environment variables from .env file if it exists."""
        # Look for .env file in project root (agent/../.env)
        project_root = Path(__file__).resolve().parent.parent
        env_file = project_root / ".env"
        
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    # Parse KEY=VALUE format
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value
    
    # API Key getters
    def get_openai_api_key(self) -> str | None:
        """Get OpenAI API key from environment or config."""
        return os.getenv("OPENAI_API_KEY")
    
    def get_anthropic_api_key(self) -> str | None:
        """Get Anthropic API key from environment or config."""
        return os.getenv("ANTHROPIC_API_KEY")
    
    def get_gemini_api_key(self) -> str | None:
        """Get Google Gemini API key from environment or config."""
        return os.getenv("GEMINI_API_KEY")
    
    def get_api_key(self, provider: str | None = None) -> str | None:
        """
        Get API key for a specific provider.
        
        Args:
            provider: Provider name (openai, anthropic, gemini, etc.)
                     If None, tries to infer from model name or uses default
        
        Returns:
            API key string or None
        """
        if provider:
            provider_lower = provider.lower()
            if provider_lower == "openai":
                return self.get_openai_api_key()
            elif provider_lower == "anthropic":
                return self.get_anthropic_api_key()
            elif provider_lower == "gemini" or provider_lower == "google":
                return self.get_gemini_api_key()
        
        # Try to infer from environment
        # Check common environment variable names
        api_key = os.getenv("API_KEY")
        if api_key:
            return api_key
        
        # Try provider-specific keys
        return (
            self.get_openai_api_key() or
            self.get_anthropic_api_key() or
            self.get_gemini_api_key()
        )
    
    # Configuration getters with defaults
    def get_backend_url(self) -> str:
        """Get backend URL."""
        return os.getenv("BACKEND_URL", self.DEFAULT_BACKEND_URL)
    
    def get_frontend_url(self) -> str:
        """Get frontend URL."""
        return os.getenv("FRONTEND_URL", self.DEFAULT_FRONTEND_URL)
    
    def get_game_name(self) -> str:
        """Get game name."""
        return os.getenv("GAME_NAME", self.DEFAULT_GAME_NAME)
    
    def get_reasoning_method(self) -> str:
        """Get reasoning method name."""
        return os.getenv("REASONING_METHOD", self.DEFAULT_REASONING_METHOD)
    
    def get_model(self) -> str:
        """Get model name."""
        return os.getenv("MODEL", self.DEFAULT_MODEL)
    
    def get_api_provider(self) -> str:
        """Get API provider name."""
        return os.getenv("API_PROVIDER", self.DEFAULT_API_PROVIDER)
    
    def get_api_base(self) -> str | None:
        """Get API base URL (for local models or custom endpoints)."""
        return os.getenv("API_BASE")
    
    def get_temperature(self) -> float:
        """Get temperature setting."""
        return float(os.getenv("TEMPERATURE", str(self.DEFAULT_TEMPERATURE)))
    
    def get_max_tokens(self) -> int:
        """Get max tokens setting."""
        return int(os.getenv("MAX_TOKENS", str(self.DEFAULT_MAX_TOKENS)))
    
    def get_max_steps(self) -> int | None:
        """Get max steps (0 or None means infinite)."""
        max_steps = int(os.getenv("MAX_STEPS", str(self.DEFAULT_MAX_STEPS)))
        return max_steps if max_steps > 0 else None
    
    def get_delay(self) -> float:
        """Get delay between steps."""
        return float(os.getenv("DELAY", str(self.DEFAULT_DELAY)))
    
    def get_auto_open_browser(self) -> bool:
        """Get auto-open browser setting."""
        value = os.getenv("AUTO_OPEN_BROWSER", str(self.DEFAULT_AUTO_OPEN_BROWSER))
        return value.lower() in ("true", "1", "yes")
    
    def get_session_id(self) -> str | None:
        """Get session ID if specified."""
        return os.getenv("SESSION_ID")


# Global config instance
config = Config()
