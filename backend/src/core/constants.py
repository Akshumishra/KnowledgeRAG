from typing import ClassVar


class DefaultLLMProviders:
    """Default LLM Providers to seed the database."""

    PROVIDERS: ClassVar[list[dict]] = [
        {
            "slug": "openai",
            "name": "OpenAI",
            "default_models": "gpt-4.1-mini, gpt-4.1-nano, gpt-5-nano",
            "is_local": False,
        },
        {
            "slug": "gemini",
            "name": "Google Gemini",
            "default_models": "gemini-1.5-pro, gemini-1.5-flash",
            "is_local": False,
        },
        {
            "slug": "groq",
            "name": "Groq",
            "default_models": "llama3-8b-8192, llama3-70b-8192",
            "is_local": False,
        },
        {
            "slug": "openrouter",
            "name": "OpenRouter",
            "default_models": "google/gemini-1.5-pro, openai/gpt-4o",
            "is_local": False,
        },
        {
            "slug": "ollama",
            "name": "Ollama (Local)",
            "default_models": "llama3, mistral",
            "is_local": True,
        },
    ]


class LLMModelConstants:
    """Default models for various providers."""

    DEFAULT_GROQ_MODEL = "llama3-8b-8192"
    DEFAULT_OLLAMA_MODEL = "llama3"
    DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o"
