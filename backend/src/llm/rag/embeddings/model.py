import logging
from openai import AsyncOpenAI
from src.core.config import settings
from typing import List

logger = logging.getLogger(__name__)


class OpenAIEmbedder:
    def __init__(self):
        self.api_key = settings.openai_api_key
        if not self.api_key:
            logger.warning(
                "OpenAI API key not found in settings! Embeddings will fail."
            )
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = "text-embedding-3-small"

    async def encode(
        self, texts: List[str], normalize_embeddings: bool = True
    ) -> List[List[float]]:
        if not texts:
            return []

        try:
            response = await self.client.embeddings.create(
                input=texts, model=self.model
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error("OpenAI Embedding failed: %s", e)
            raise


_embedding_model = None


def get_embedding_model() -> OpenAIEmbedder:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = OpenAIEmbedder()
    return _embedding_model
