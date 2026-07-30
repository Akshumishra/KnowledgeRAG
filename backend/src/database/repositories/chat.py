
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.repositories.base import BaseRepository
from src.models.chat import Conversation, Message


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, session: AsyncSession):
        super().__init__(Conversation, session)

    async def list_by_user(self, user_id: str, workspace_id: str) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.workspace_id == workspace_id,
                Conversation.deleted_at.is_(None),
            )
            .order_by(Conversation.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class MessageRepository(BaseRepository[Message]):
    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)

    async def list_by_conversation(self, conversation_id: str) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_token_usage_stats(self, workspace_id: str):
        stmt = (
            select(
                func.sum(Message.prompt_tokens),
                func.sum(Message.completion_tokens),
                func.sum(Message.total_tokens),
                func.avg(Message.latency_ms),
                func.count(Message.id),
            )
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.workspace_id == workspace_id)
        )
        result = await self.session.execute(stmt)
        return result.one()
