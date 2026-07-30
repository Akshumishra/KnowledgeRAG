from src.providers.llm.base import BaseLLMProvider
from src.providers.llm.gemini import GeminiProvider
from src.providers.llm.groq import GroqProvider
from src.providers.llm.ollama import OllamaProvider
from src.providers.llm.openai import OpenAIProvider
from src.providers.llm.openrouter import OpenRouterProvider


def get_provider(provider_id: str, api_key: str) -> BaseLLMProvider:
    if provider_id == "openai":
        return OpenAIProvider(api_key=api_key)
    elif provider_id == "ollama":
        return OllamaProvider(base_url=api_key)
    elif provider_id == "gemini":
        return GeminiProvider(api_key=api_key)
    elif provider_id == "groq":
        return GroqProvider(api_key=api_key)
    elif provider_id == "openrouter":
        return OpenRouterProvider(api_key=api_key)
    else:
        raise ValueError(f"Unknown LLM provider: {provider_id}")
