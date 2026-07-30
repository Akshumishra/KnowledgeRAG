import json
from collections.abc import AsyncGenerator

import httpx
from src.core.constants import LLMModelConstants
from src.providers.llm.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def generate(self, prompt: str, system_prompt: str, **kwargs) -> str:
        model = kwargs.get("model", LLMModelConstants.DEFAULT_OLLAMA_MODEL)
        messages = kwargs.get("messages")
        if not messages:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

        payload = {"model": model, "messages": messages, "stream": False}
        if "temperature" in kwargs:
            payload["options"] = {"temperature": kwargs["temperature"]}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat", json=payload, timeout=600.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")

    async def stream(
        self, prompt: str, system_prompt: str, **kwargs
    ) -> AsyncGenerator[str, None]:
        model = kwargs.get("model", LLMModelConstants.DEFAULT_OLLAMA_MODEL)
        messages = kwargs.get("messages")
        if not messages:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

        payload = {"model": model, "messages": messages, "stream": True}
        if "temperature" in kwargs:
            payload["options"] = {"temperature": kwargs["temperature"]}

        async with httpx.AsyncClient() as client, client.stream(
            "POST", f"{self.base_url}/api/chat", json=payload, timeout=600.0
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        pass

    async def list_models(self) -> list[dict[str, str]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=30.0)
                response.raise_for_status()
                data = response.json()
                models = [
                    {"id": m["name"], "name": m["name"]} for m in data.get("models", [])
                ]
                models.sort(key=lambda x: x["name"])
                return models
        except Exception:  # noqa: BLE001
            return []

    def supports_streaming(self) -> bool:
        return True
