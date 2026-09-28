"""
AI Provider interface, MockAIProvider, and LiteLLMAIProvider.

AI must be behind an interface/protocol so the
implementation can later replace a mock provider with a real model provider.

The LiteLLMAIProvider uses LiteLLM to connect to any LLM-compatible
endpoint (e.g., LM Studio, OpenAI, Ollama, etc.) configured via AppSettings.
"""

import json
from typing import Protocol

import litellm

from config.settings import LiteLLMSettings


class AIProvider(Protocol):
    """Protocol defining the contract for AI-assisted operations.

    Any real or mock AI provider must implement these methods.
    The system can swap between a MockAIProvider (for testing and
    deterministic behavior) and a LiteLLMAIProvider (for real LLM
    inference) without changing the calling code.
    """

    def classify_category(self, description: str) -> str:
        """Suggest a category classification for the given item description."""
        ...

    def normalize_description(self, description: str) -> str:
        """Suggest a normalized/cleaned version of the item description."""
        ...


class MockAIProvider:
    """Mock AI provider for testing and development.

    Uses simple heuristic keyword matching to simulate AI behavior.
    This can be replaced with a LiteLLMAIProvider by setting
    AI_PROVIDER=litellm in your environment.
    """

    # Keyword-to-category mapping for mock classification
    CATEGORY_KEYWORDS = {
        "bearing": "Mechanical",
        "gear": "Mechanical",
        "shaft": "Mechanical",
        "valve": "Mechanical",
        "pump": "Mechanical",
        "o-ring": "Mechanical",
        "gasket": "Mechanical",
        "cable": "Electrical",
        "wire": "Electrical",
        "resistor": "Electrical",
        "capacitor": "Electrical",
        "transformer": "Electrical",
        "fuse": "Electrical",
        "switch": "Electrical",
        "pipe": "Plumbing",
        "fitting": "Plumbing",
        "flange": "Plumbing",
    }

    def classify_category(self, description: str) -> str:
        """Mock classification using keyword matching."""
        desc_lower = description.lower()
        for keyword, category in self.CATEGORY_KEYWORDS.items():
            if keyword in desc_lower:
                return category
        return "General"

    def normalize_description(self, description: str) -> str:
        """Mock normalization: strip, collapse whitespace, title-case."""
        if not description or not description.strip():
            return description or ""
        # Strip leading/trailing whitespace
        normalized = description.strip()
        # Collapse multiple spaces into one
        normalized = " ".join(normalized.split())
        # Title-case
        normalized = normalized.title()
        return normalized


class LiteLLMAIProvider:
    """AI provider backed by LiteLLM for real LLM inference.

    Connects to any LiteLLM-compatible endpoint such as:
      - LM Studio (local)
      - OpenAI API
      - Ollama
      - Azure OpenAI
      - Any OpenAI-compatible server

    Configuration is provided via LiteLLMSettings (loaded from env vars).
    """

    VALID_CATEGORIES = [
        "Mechanical", "Electrical", "Plumbing", "Safety",
        "Instrumentation", "General", "Chemical", "Structural",
    ]

    def __init__(self, settings: LiteLLMSettings):
        self.model = settings.model
        self.api_base = settings.api_base
        self.api_key = settings.api_key
        self.temperature = settings.temperature
        self.max_tokens = settings.max_tokens

        # Suppress LiteLLM's verbose logging
        litellm.suppress_debug_info = True

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Make a completion call via LiteLLM."""
        try:
            response = litellm.completion(
                model=self.model,
                api_base=self.api_base,
                api_key=self.api_key,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            # Fail gracefully — return empty so the rule can handle it
            print(f"[LiteLLMAIProvider] LLM call failed: {e}")
            return ""

    def classify_category(self, description: str) -> str:
        """Classify the item description into a category using the LLM."""
        categories_str = ", ".join(self.VALID_CATEGORIES)
        system_prompt = (
            "You are a data quality assistant for an enterprise item-master system. "
            "Your job is to classify item descriptions into categories. "
            f"Valid categories are: {categories_str}. "
            "Respond with ONLY the category name, nothing else."
        )
        user_prompt = f"Classify this item description into a category: \"{description}\""

        result = self._call_llm(system_prompt, user_prompt)

        # Validate the response is one of our known categories
        for cat in self.VALID_CATEGORIES:
            if cat.lower() in result.lower():
                return cat

        # If LLM returned something unexpected, fall back to General
        return "General"

    def normalize_description(self, description: str) -> str:
        """Suggest a normalized description using the LLM."""
        system_prompt = (
            "You are a data quality assistant. Normalize the following item description: "
            "fix casing, remove extra whitespace, expand abbreviations, and make it "
            "clear and professional. Respond with ONLY the normalized description, "
            "nothing else. Do not add quotes around it."
        )
        user_prompt = f"Normalize this item description: \"{description}\""

        result = self._call_llm(system_prompt, user_prompt)

        # If LLM call failed, return original
        if not result:
            return description

        # Strip any quotes the LLM may have added
        result = result.strip().strip('"').strip("'")
        return result


def create_ai_provider(settings=None):
    """Factory function to create the appropriate AI provider based on settings.

    Usage:
        from config.settings import AppSettings
        settings = AppSettings.from_env()
        ai = create_ai_provider(settings)
    """
    from config.settings import AppSettings

    if settings is None:
        settings = AppSettings.from_env()

    if settings.ai_provider == "litellm":
        return LiteLLMAIProvider(settings.litellm)
    else:
        return MockAIProvider()
