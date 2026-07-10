from typing import AsyncGenerator, Dict, List
from google import genai
from google.genai import types

from src.providers.llm.base import BaseLLMProvider
from src.llm.rag.constant import RAGConstant


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=self.api_key)

    async def generate(self, prompt: str, system_prompt: str, **kwargs) -> str:
        model_name = kwargs.get("model", RAGConstant.GEMINI_DEFAULT_MODEL)

        config_kwargs = {}
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt
        
        messages = kwargs.get("messages")
        if messages:
            contents = []
            for msg in messages:
                if msg["role"] == "system":
                    continue
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
            response = await self.client.aio.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
            )
            return response.text
        else:
            response = await self.client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
            )
            return response.text

    async def stream(
        self, prompt: str, system_prompt: str, **kwargs
    ) -> AsyncGenerator[str, None]:
        model_name = kwargs.get("model", RAGConstant.GEMINI_DEFAULT_MODEL)

        config_kwargs = {}
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt

        messages = kwargs.get("messages")
        if messages:
            contents = []
            for msg in messages:
                if msg["role"] == "system":
                    continue
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
            response_stream = await self.client.aio.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
            )
        else:
            response_stream = await self.client.aio.models.generate_content_stream(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
            )

        async for chunk in response_stream:
            if chunk.text:
                yield chunk.text

    async def list_models(self) -> List[Dict[str, str]]:
        return RAGConstant.FALLBACK_GEMINI_MODELS

    def supports_streaming(self) -> bool:
        return True
