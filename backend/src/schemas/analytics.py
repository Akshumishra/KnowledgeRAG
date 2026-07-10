from __future__ import annotations

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_documents: int
    total_chunks: int
    total_users: int
    total_conversations: int
    total_messages: int
    total_tokens_used: int
    avg_response_latency_ms: float
    storage_used_bytes: int
    active_collections: int


class TokenUsageByDay(BaseModel):
    date: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class AnalyticsResponse(BaseModel):
    stats: DashboardStats
    token_usage_7d: list[TokenUsageByDay]
