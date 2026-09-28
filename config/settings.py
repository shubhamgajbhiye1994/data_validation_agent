"""
Application settings for the Data Quality Assistant.

Configuration is loaded from environment variables or a .env file.
This allows the user to point the AI provider at their own LLM Studio
instance (or any LiteLLM-compatible endpoint) without modifying code.

Environment Variables:
    AI_PROVIDER        : "litellm" or "mock" (default: "mock")
    LITELLM_MODEL      : Model identifier for LiteLLM (e.g. "openai/google/gemma-4-26b-a4b-qat")
    LITELLM_API_BASE   : Base URL for the LLM API (e.g. "http://192.168.0.101:1234/v1")
    LITELLM_API_KEY    : API key (default: "not-needed" for local LLM Studio)
    LITELLM_TEMPERATURE: Temperature for generation (default: 0.2)
    LITELLM_MAX_TOKENS : Max tokens for generation (default: 256)
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


@dataclass
class LiteLLMSettings:
    """Settings for the LiteLLM-backed AI provider."""
    model: str = "openai/google/gemma-4-26b-a4b-qat"
    api_base: str = "http://192.168.0.101:1234/v1"
    api_key: str = "not-needed"
    temperature: float = 0.2
    max_tokens: int = 256


@dataclass
class AppSettings:
    """Top-level application settings."""
    ai_provider: str = "mock"  # "mock" or "litellm"
    litellm: LiteLLMSettings = field(default_factory=LiteLLMSettings)

    @classmethod
    def from_env(cls) -> "AppSettings":
        """Load settings from .env file and environment variables."""
        load_dotenv()  # Auto-load .env file if present
        litellm_settings = LiteLLMSettings(
            model=os.environ.get("LITELLM_MODEL", "openai/google/gemma-4-26b-a4b-qat"),
            api_base=os.environ.get("LITELLM_API_BASE", "http://192.168.0.101:1234/v1"),
            api_key=os.environ.get("LITELLM_API_KEY", "not-needed"),
            temperature=float(os.environ.get("LITELLM_TEMPERATURE", "0.2")),
            max_tokens=int(os.environ.get("LITELLM_MAX_TOKENS", "256")),
        )
        return cls(
            ai_provider=os.environ.get("AI_PROVIDER", "mock"),
            litellm=litellm_settings,
        )
