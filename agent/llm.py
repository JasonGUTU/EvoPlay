"""Unified LLM interface using LiteLLM as middleware.

This module provides a simple, unified interface to call language models
through LiteLLM, abstracting away the differences between different providers.
"""

from __future__ import annotations

import os
from typing import Any


class LLM:
    """
    Unified interface for calling language models via LiteLLM.
    
    This is a simple wrapper around LiteLLM that provides a consistent API
    regardless of which model provider you're using (OpenAI, Anthropic, Google, etc.).
    """
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",  # Default model (check OpenAI docs for latest)
        api_key: str | None = None,
        api_provider: str | None = None,
        api_base: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        """
        Initialize the LLM interface.
        
        Args:
            model: Model identifier (e.g., "gpt-4", "claude-3-sonnet-20240229", "gemini/gemini-pro")
            api_key: API key for the provider (if None, will read from environment)
            api_provider: Provider name (openai, anthropic, gemini, etc.) - auto-detected if None
            api_base: API base URL (for local models or custom endpoints)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens in response
        """
        # Delay import of litellm to avoid initialization errors
        # Import it only when needed (lazy import)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._litellm = None  # Will be imported lazily
        
        # Set API key if provided
        if api_key:
            self._set_api_key(api_key, api_provider, model)
        
        # Set API base if provided
        if api_base:
            self._set_api_base(api_base, model)
    
    def _set_api_key(self, api_key: str, api_provider: str | None, model: str) -> None:
        """Set API key in appropriate environment variable."""
        provider = api_provider
        if not provider:
            # Auto-detect provider from model name
            if model.startswith("gpt") or model.startswith("azure/"):
                provider = "openai"
            elif model.startswith("claude"):
                provider = "anthropic"
            elif model.startswith("gemini"):
                provider = "gemini"
            elif model.startswith("ollama"):
                provider = "ollama"
        
        # Set environment variable
        if provider == "openai":
            os.environ["OPENAI_API_KEY"] = api_key
        elif provider == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = api_key
        elif provider == "gemini" or provider == "google":
            os.environ["GEMINI_API_KEY"] = api_key
        elif provider == "ollama":
            # Ollama doesn't require API key
            pass
        else:
            # Default to OpenAI
            os.environ["OPENAI_API_KEY"] = api_key
    
    def _set_api_base(self, api_base: str, model: str) -> None:
        """Set API base URL."""
        if model.startswith("ollama"):
            os.environ["OLLAMA_API_BASE"] = api_base
        else:
            os.environ["OPENAI_API_BASE"] = api_base
    
    def _ensure_litellm(self):
        """Lazy import of litellm to avoid initialization errors."""
        if self._litellm is None:
            try:
                import litellm
                self._litellm = litellm
                # Configure LiteLLM
                try:
                    self._litellm.set_verbose = False
                except Exception:
                    # Some versions of litellm may not have set_verbose
                    pass
            except ImportError as e:
                raise ImportError(
                    f"Failed to import litellm: {e}\n"
                    "Please install it with: pip install litellm"
                ) from e
            except Exception as e:
                # Handle other initialization errors (like InputAudio)
                raise RuntimeError(
                    f"Failed to initialize litellm: {e}\n"
                    "This might be a version compatibility issue.\n"
                    "Try: pip install --upgrade litellm\n"
                    "Or: pip install litellm==1.40.0"
                ) from e
    
    def call(
        self,
        messages: list[dict[str, str]],
        system_message: str | None = None,
        **kwargs: Any
    ) -> str:
        """
        Call the language model with messages.
        
        Args:
            messages: List of message dicts with "role" and "content" keys
                     Example: [{"role": "user", "content": "Hello"}]
            system_message: Optional system message (will be prepended to messages)
            **kwargs: Additional parameters to pass to LiteLLM (e.g., temperature, max_tokens)
        
        Returns:
            Response text from the model
        """
        # Ensure litellm is imported
        self._ensure_litellm()
        
        # Prepare messages
        full_messages = []
        if system_message:
            full_messages.append({"role": "system", "content": system_message})
        full_messages.extend(messages)
        
        # Merge kwargs with instance defaults
        call_kwargs = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            **kwargs
        }
        
        # Call LiteLLM
        response = self._litellm.completion(
            model=self.model,
            messages=full_messages,
            **call_kwargs
        )
        
        return response.choices[0].message.content.strip()
    
    def simple_call(self, prompt: str, system_message: str | None = None, **kwargs: Any) -> str:
        """
        Simple call with a single user prompt.
        
        Args:
            prompt: User prompt text
            system_message: Optional system message
            **kwargs: Additional parameters
        
        Returns:
            Response text from the model
        """
        return self.call(
            messages=[{"role": "user", "content": prompt}],
            system_message=system_message,
            **kwargs
        )
