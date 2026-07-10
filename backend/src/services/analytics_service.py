"""
Analytics service using UoW and Repositories.
"""

from typing import Dict, Any
from src.database.uow import UnitOfWork
from src.database.repositories.chat import MessageRepository
from src.models.auth import User
from src.core.exceptions import ForbiddenError


class AnalyticsService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_dashboard_metrics(
        self, workspace_id: str, actor: User
    ) -> Dict[str, Any]:
        if not getattr(actor, "is_owner", False):
            raise ForbiddenError()

        async with self.uow:
            msg_repo = MessageRepository(self.uow.session)
            stats = await msg_repo.get_token_usage_stats(workspace_id)
            return {
                "total_prompt_tokens": int(stats[0] or 0),
                "total_completion_tokens": int(stats[1] or 0),
                "total_tokens": int(stats[2] or 0),
                "total_context_tokens": int(stats[3] or 0),
                "total_retrieved_tokens": int(stats[4] or 0),
                "average_latency_ms": round(float(stats[5] or 0), 2),
                "total_messages": int(stats[6] or 0),
            }
