"""
Context Builder and Token Budget Manager.
"""

from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class TokenBudgetManager:
    """
    Tracks and enforces token limits across the RAG pipeline.
    """

    def __init__(self, max_context_window: int, prompt_tokens: int = 0):
        self.max_context_window = max_context_window
        self.used_tokens = prompt_tokens
        self.prompt_tokens = prompt_tokens
        self.context_tokens = 0

    def add_tokens(self, count: int) -> bool:
        """
        Attempt to add tokens to the budget.
        Returns True if successful, False if it exceeds the limit.
        """
        if self.used_tokens + count > self.max_context_window:
            return False
        self.used_tokens += count
        self.context_tokens += count
        return True

    def get_remaining(self) -> int:
        return max(0, self.max_context_window - self.used_tokens)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Returns metrics required by the frontend UI.
        """
        return {
            "context_used": self.used_tokens,
            "prompt_tokens": self.prompt_tokens,
            "context_tokens": self.context_tokens,
            "context_limit": self.max_context_window,
            "remaining": self.get_remaining(),
            "percentage": (
                round((self.used_tokens / self.max_context_window) * 100, 1)
                if self.max_context_window > 0
                else 0.0
            ),
        }


class ContextBuilder:
    """
    Assembles prompt context from retrieved chunks while strictly adhering to token budgets.
    """

    def __init__(self, llm_provider):
        """
        Initialize with a specific LLM Provider (to use its count_tokens logic).
        """
        self.llm_provider = llm_provider

    def build_context(
        self,
        system_prompt: str,
        user_query: str,
        retrieved_chunks: List[Dict[str, Any]],
        model_name: str,
        chat_history: List[Dict[str, str]] = None,
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Constructs the final prompt string, filtering out chunks that exceed the token budget.
        Returns:
            Tuple containing: (Final assembled messages, Accepted chunks, Metrics dictionary)
        """
        max_tokens = self.llm_provider.maximum_context_window(model_name)
        chat_history = chat_history or []

        history_tokens = sum(
            self.llm_provider.count_tokens(m.get("content", "")) for m in chat_history
        )

        base_tokens = self.llm_provider.count_tokens(
            system_prompt
        ) + self.llm_provider.count_tokens(user_query)

        budget_manager = TokenBudgetManager(max_tokens, base_tokens + history_tokens)

        accepted_chunks = []
        context_text = ""

        for chunk in retrieved_chunks:
            chunk_str = f"- Source: {chunk.get('document_name', 'Unknown')}, Page: {chunk.get('page', '?')}\n  Content: {chunk.get('text', '')}\n\n"
            chunk_tokens = self.llm_provider.count_tokens(chunk_str)

            if budget_manager.add_tokens(chunk_tokens):
                context_text += chunk_str
                accepted_chunks.append(chunk)
            else:
                logger.warning(
                    f"Context window full. Dropped chunk from {chunk.get('document_name')}"
                )
                break

        final_messages = []
        if system_prompt:
            final_messages.append({"role": "system", "content": system_prompt})

        final_messages.extend(chat_history)

        augmented_query = user_query
        if context_text:
            augmented_query += f"\n\nContext:\n{context_text}"

        final_messages.append({"role": "user", "content": augmented_query})

        metrics = budget_manager.get_metrics()

        return final_messages, accepted_chunks, metrics
