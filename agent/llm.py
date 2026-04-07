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
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        api_provider: str | None = None,
        api_base: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        no_thinking: bool = False,
        extra_headers: dict | None = None,
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
        self.no_thinking = no_thinking
        self._extra_headers = extra_headers or {}
        self._litellm = None  # Will be imported lazily
        self._api_base = api_base
        self._api_key = api_key
        
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
        # Some newer models (gpt-5.4+) require max_completion_tokens instead of max_tokens
        token_param = "max_tokens"
        if self.model.startswith("gpt-5") or self.model.startswith("o1") or self.model.startswith("o3"):
            token_param = "max_completion_tokens"
        call_kwargs = {
            "temperature": self.temperature,
            token_param: self.max_tokens,
            **kwargs
        }

        # Use direct HTTP for custom api_base (litellm drops reasoning_content)
        if self._api_base:
            return self._direct_api_call(full_messages, call_kwargs)

        # Call LiteLLM for standard providers with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                call_kwargs["timeout"] = 60
                response = self._litellm.completion(
                    model=self.model,
                    messages=full_messages,
                    **call_kwargs
                )
                break
            except Exception as e:
                print(f"  [LLM] API call error (attempt {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
                import time
                time.sleep(2 ** attempt)

        # Store token usage from response
        usage = getattr(response, "usage", None)
        self.last_usage = {
            "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
            "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        }

        content = response.choices[0].message.content or ""
        # Strip thinking tags if present
        if "</think>" in content:
            content = content.split("</think>")[-1]
        return content.strip()
    
    def _direct_api_call(self, messages: list, call_kwargs: dict) -> str:
        """Direct HTTP call to custom API base, preserving reasoning_content."""
        import json
        import urllib.request

        # Extract model name (strip openai/ prefix if present)
        model_name = self.model
        if model_name.startswith("openai/"):
            model_name = model_name[7:]

        url = self._api_base.rstrip("/") + "/chat/completions"
        max_tok = call_kwargs.get("max_tokens", self.max_tokens)

        body = {
            "model": model_name,
            "messages": messages,
            "temperature": call_kwargs.get("temperature", self.temperature),
            "max_tokens": max_tok,
        }

        # Disable thinking mode if requested
        if self.no_thinking:
            body["enable_thinking"] = False
        else:
            # Thinking models need much higher max_tokens
            if max_tok < 4096:
                body["max_tokens"] = 4096

        api_key = self._api_key or os.environ.get("OPENAI_API_KEY", "")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self._extra_headers)
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers=headers,
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = urllib.request.urlopen(req, timeout=60)
                result = json.loads(resp.read())
                break
            except Exception as e:
                print(f"  [LLM] API call timeout/error (attempt {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
                import time
                time.sleep(2 ** attempt)
                # Recreate request (urlopen consumes it)
                req = urllib.request.Request(
                    url,
                    data=json.dumps(body).encode(),
                    headers=headers,
                )

        # Extract usage
        usage_data = result.get("usage", {})
        self.last_usage = {
            "input_tokens": usage_data.get("prompt_tokens", 0),
            "output_tokens": usage_data.get("completion_tokens", 0),
        }

        # Get content — check both content and reasoning_content
        msg = result["choices"][0]["message"]
        content = msg.get("content", "") or ""

        # Strip thinking tags if present
        if "</think>" in content:
            content = content.split("</think>")[-1]
        return content.strip()

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
