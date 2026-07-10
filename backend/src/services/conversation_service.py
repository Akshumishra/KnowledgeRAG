from typing import List
from src.core.exceptions import NotFoundError, ForbiddenError
from src.database.uow import UnitOfWork
from src.database.repositories.chat import ConversationRepository, MessageRepository
from src.models.auth import User
from src.models.chat import Conversation
from src.schemas.chat import ConversationResponse, ConversationCreate, MessageResponse


class ConversationService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def list_conversations(self, user: User) -> List[ConversationResponse]:
        async with self.uow:
            repo = ConversationRepository(self.uow.session)
            convs = await repo.list_by_user(user.id, user.workspace_id)
            return [
                ConversationResponse(id=c.id, title=c.title, created_at=c.created_at)
                for c in convs
            ]

    async def create_conversation(
        self, data: ConversationCreate, user: User
    ) -> ConversationResponse:
        async with self.uow:
            repo = ConversationRepository(self.uow.session)
            conv = repo.add(
                Conversation(
                    workspace_id=user.workspace_id, user_id=user.id, title=data.title
                )
            )
            await self.uow.commit()
            return ConversationResponse(
                id=conv.id, title=conv.title, created_at=conv.created_at
            )

    async def get_conversation(self, conversation_id: str, user: User):
        async with self.uow:
            conv_repo = ConversationRepository(self.uow.session)
            msg_repo = MessageRepository(self.uow.session)

            conv = await conv_repo.get(conversation_id)
            if not conv or conv.workspace_id != user.workspace_id:
                raise NotFoundError("Conversation", conversation_id)

            if conv.user_id != user.id and not getattr(user, "is_owner", False):
                raise ForbiddenError()

            msgs = await msg_repo.list_by_conversation(conversation_id)
            import json

            from src.schemas.chat import ConversationDetailResponse, MessageResponse

            return ConversationDetailResponse(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                messages=[
                    MessageResponse(
                        id=m.id,
                        role=m.role,
                        content=m.content,
                        status=m.status,
                        created_at=m.created_at,
                        sources=json.loads(m.sources_json) if m.sources_json else [],
                        prompt_tokens=m.prompt_tokens,
                        completion_tokens=m.completion_tokens,
                        total_tokens=m.total_tokens,
                        model_id=m.model_id,
                        latency_ms=m.latency_ms,
                    )
                    for m in msgs
                ],
            )

    async def get_messages(
        self, conversation_id: str, user: User
    ) -> List[MessageResponse]:
        async with self.uow:
            conv_repo = ConversationRepository(self.uow.session)
            msg_repo = MessageRepository(self.uow.session)

            conv = await conv_repo.get(conversation_id)
            if not conv or conv.workspace_id != user.workspace_id:
                raise NotFoundError("Conversation", conversation_id)

            if conv.user_id != user.id and not getattr(user, "is_owner", False):
                raise ForbiddenError()

            msgs = await msg_repo.list_by_conversation(conversation_id)
            import json

            return [
                MessageResponse(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    status=m.status,
                    created_at=m.created_at,
                    sources=json.loads(m.sources_json) if m.sources_json else [],
                    prompt_tokens=m.prompt_tokens,
                    completion_tokens=m.completion_tokens,
                    total_tokens=m.total_tokens,
                    model_id=m.model_id,
                    latency_ms=m.latency_ms,
                )
                for m in msgs
            ]

    async def delete_conversation(self, conversation_id: str, user: User) -> None:
        async with self.uow:
            conv_repo = ConversationRepository(self.uow.session)
            conv = await conv_repo.get(conversation_id)
            if not conv or conv.workspace_id != user.workspace_id:
                raise NotFoundError("Conversation", conversation_id)

            if conv.user_id != user.id:
                raise ForbiddenError()

            from datetime import datetime, timezone
            from sqlalchemy import update
            from src.models.chat import Conversation

            stmt = (
                update(Conversation)
                .where(Conversation.id == conversation_id)
                .values(deleted_at=datetime.now(timezone.utc))
            )
            await self.uow.session.execute(stmt)
            await self.uow.commit()
