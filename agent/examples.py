"""Example usage of the agent with different models via LiteLLM."""

from __future__ import annotations

from agent.agent import Agent
from agent.reasoning import LiteLLMReasoning


def example_openai():
    """Example: Using OpenAI GPT models."""
    reasoning = LiteLLMReasoning(
        model="gpt-4",
        api_key="your-openai-api-key",  # Or set OPENAI_API_KEY env var
        temperature=0.7,
    )
    
    agent = Agent(reasoning=reasoning, game_name="2048")
    agent.run_loop(max_steps=10, delay=1.0)


def example_claude():
    """Example: Using Anthropic Claude models."""
    reasoning = LiteLLMReasoning(
        model="claude-3-sonnet-20240229",
        api_key="your-anthropic-api-key",  # Or set ANTHROPIC_API_KEY env var
        temperature=0.7,
    )
    
    agent = Agent(reasoning=reasoning, game_name="2048")
    agent.run_loop(max_steps=10, delay=1.0)


def example_gemini():
    """Example: Using Google Gemini models."""
    reasoning = LiteLLMReasoning(
        model="gemini/gemini-pro",
        api_key="your-gemini-api-key",  # Or set GEMINI_API_KEY env var
        temperature=0.7,
    )
    
    agent = Agent(reasoning=reasoning, game_name="2048")
    agent.run_loop(max_steps=10, delay=1.0)


def example_ollama():
    """Example: Using local Ollama models."""
    reasoning = LiteLLMReasoning(
        model="ollama/llama2",
        api_base="http://localhost:11434",  # Ollama default port
        temperature=0.7,
    )
    
    agent = Agent(reasoning=reasoning, game_name="2048")
    agent.run_loop(max_steps=10, delay=1.0)


def example_azure_openai():
    """Example: Using Azure OpenAI."""
    reasoning = LiteLLMReasoning(
        model="azure/gpt-4",
        api_key="your-azure-api-key",
        api_base="https://your-resource.openai.azure.com/",
        temperature=0.7,
    )
    
    agent = Agent(reasoning=reasoning, game_name="2048")
    agent.run_loop(max_steps=10, delay=1.0)


if __name__ == "__main__":
    # Uncomment the example you want to run:
    # example_openai()
    # example_claude()
    # example_gemini()
    # example_ollama()
    # example_azure_openai()
    pass
