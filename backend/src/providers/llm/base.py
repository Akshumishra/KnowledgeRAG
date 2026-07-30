import abc
from collections.abc import AsyncGenerator


class BaseLLMProvider(abc.ABC):
    """
    Abstract interface for interacting with LLM providers (OpenAI, Gemini, local, etc.).
    """

    @abc.abstractmethod
    async def generate(self, prompt: str, system_prompt: str, **kwargs) -> str:
        """
        Generate a complete response.
        """

    @abc.abstractmethod
    async def stream(
        self, prompt: str, system_prompt: str, **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Generate a response incrementally.
        """

    def count_tokens(self, text: str) -> int:
        """
        Count tokens for a given text string.
        """
        return len(text) // 4

    @abc.abstractmethod
    async def list_models(self) -> list[dict[str, str]]:
        """
        List available models from this provider.
        """

    @abc.abstractmethod
    def supports_streaming(self) -> bool:
        """
        Return True if the provider/model supports streaming.
        """

    def maximum_context_window(self, model: str) -> int:
        """
        Return the maximum context window size (in tokens) for a given model.
        """
        return 8192
