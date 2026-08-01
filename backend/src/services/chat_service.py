import asyncio
import builtins
import json
import json as _json
import logging
import time
import traceback
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import select, update

from src.core.crypto import decrypt
from src.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from src.database.repositories.chat import (
    ConversationRepository,
    MessageRepository,
)
from src.database.repositories.workspace import WorkspaceAPIKeyRepository
from src.database.uow import UnitOfWork
from src.llm.capability_discovery import (
    DiscoveryService,
    _extract_unsupported_param,
)
from src.llm.capability_manager import ModelCapabilityManager
from src.llm.rag.context import ContextBuilder
from src.llm.rag.retrieval.search import Retriever
from src.models.auth import User
from src.models.chat import Message
from src.models.knowledge import Document
from src.models.settings import LLMProvider
from src.providers.llm.base import BaseLLMProvider
from src.schemas.chat import ChatRequest
from src.services.provider_service import ProviderService
from src.services.stream_manager import stream_manager

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, uow: UnitOfWork, llm_factory):
        self.uow = uow
        self.llm_factory = llm_factory

    async def get_message_status(
        self, conversation_id: str, message_id: str, workspace_id: str, actor: User
    ) -> dict:
        async with self.uow:
            conv_repo = ConversationRepository(self.uow.session)
            conv = await conv_repo.get(conversation_id)
            if not conv or conv.workspace_id != workspace_id:
                raise NotFoundError("Conversation", conversation_id)

            if conv.user_id != actor.id and not getattr(actor, "is_owner", False):
                raise ForbiddenError()

            msg_repo = MessageRepository(self.uow.session)
            msg = await msg_repo.get(message_id)
            if not msg or msg.conversation_id != conversation_id:
                raise NotFoundError("Message", message_id)

            return {
                "id": msg.id,
                "status": msg.status,
                "content": msg.content,
                "error_message": msg.error_message,
            }

    async def stream_chat(
        self,
        conversation_id: str,
        data: ChatRequest,
        workspace_id: str,
        actor: User,
        request: Request,
    ) -> AsyncGenerator[str, None]:

        async with self.uow:
            conv_repo = ConversationRepository(self.uow.session)
            msg_repo = MessageRepository(self.uow.session)
            WorkspaceAPIKeyRepository(self.uow.session)

            conv = await conv_repo.get(conversation_id)
            if not conv or conv.workspace_id != workspace_id:
                raise NotFoundError("Conversation", conversation_id)

            if conv.user_id != actor.id and not getattr(actor, "is_owner", False):
                raise ForbiddenError()

            stmt = (
                select(Message.id)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.status.in_(["thinking", "generating"]),
                )
                .limit(1)
            )
            result = await self.uow.session.execute(stmt)
            if result.first():
                raise ConflictError(
                    "A generation is already in progress for this conversation."
                )

            stmt = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
            )
            result = await self.uow.session.execute(stmt)
            db_messages = result.scalars().all()
            chat_history = [
                {"role": m.role, "content": m.content}
                for m in db_messages
                if m.status == "completed"
            ]

            msg_repo.add(
                Message(
                    conversation_id=conversation_id,
                    role="user",
                    content=data.message,
                    status="completed",
                )
            )

            generation_id = str(uuid.uuid4())
            assistant_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content="",
                status="thinking",
                generation_id=generation_id,
                started_at=datetime.now(UTC),
            )
            msg_repo.add(assistant_msg)

            await self.uow.commit()
            assistant_msg_id = assistant_msg.id

            provider_id = data.model_provider or "openai"
            model_name = data.model_name or "gpt-5-nano"

            api_key = data.api_key
            if not api_key:
                provider_service = ProviderService(self.uow)
                api_key_record = await provider_service._resolve_key(
                    provider_id, workspace_id, actor, model_name=model_name
                )
                if not api_key_record or not api_key_record.is_valid:
                    raise BadRequestError(
                        f"No valid API key configured for {provider_id}"
                    )
                api_key = decrypt(api_key_record.encrypted_key)
                
            stmt = select(LLMProvider.slug).where(LLMProvider.id == provider_id)
            slug_res = await self.uow.session.execute(stmt)
            provider_slug = slug_res.scalar() or provider_id

            llm_provider: BaseLLMProvider = self.llm_factory(provider_slug, api_key)

        queue = asyncio.Queue()

        asyncio.create_task(
            self._background_generate(
                queue,
                assistant_msg_id,
                generation_id,
                conversation_id,
                workspace_id,
                data.message,
                chat_history,
                provider_id,
                model_name,
                llm_provider,
            )
        )

        stream_manager.initialize_stream(assistant_msg_id)
        try:
            init_event = f"event: thinking\ndata: {json.dumps({'message_id': assistant_msg_id})}\n\n"
            yield init_event
            await stream_manager.push_event(assistant_msg_id, init_event)

            while True:
                if await request.is_disconnected():
                    logger.info(
                        "Client disconnected during stream. Background task will continue."
                    )
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    if event is None:
                        break

                    yield event
                except TimeoutError:
                    continue
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error in stream loop: {e}")
        finally:
            pass

    async def stream_existing_message(
        self,
        conversation_id: str,
        message_id: str,
        workspace_id: str,
        actor: User,
        request: Request,
    ) -> AsyncGenerator[str, None]:
        async with self.uow:
            conv_repo = ConversationRepository(self.uow.session)
            conv = await conv_repo.get(conversation_id)
            if not conv or conv.workspace_id != workspace_id:
                raise NotFoundError("Conversation", conversation_id)
            if conv.user_id != actor.id and not getattr(actor, "is_owner", False):
                raise ForbiddenError()

        if (
            stream_manager.is_done(message_id)
            and message_id not in stream_manager.buffers
        ):
            # If already done and buffer cleaned up, just return
            yield "event: done\ndata: {}\n\n"
            return

        # Flush existing buffer
        if message_id in stream_manager.buffers:
            for event in stream_manager.buffers[message_id]:
                yield event

        if stream_manager.is_done(message_id):
            return

        queue = asyncio.Queue()
        if message_id not in stream_manager.clients:
            stream_manager.clients[message_id] = set()
        stream_manager.clients[message_id].add(queue)

        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    if event is None:
                        break
                    yield event
                except TimeoutError:
                    continue
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error in reconnect stream loop: {e}")
        finally:
            if message_id in stream_manager.clients:
                stream_manager.clients[message_id].discard(queue)

    async def _background_generate(
        self,
        queue: asyncio.Queue,
        assistant_msg_id: str,
        generation_id: str,
        conversation_id: str,
        workspace_id: str,
        user_message: str,
        chat_history: list,
        provider_id: str,
        model_name: str,
        llm_provider: BaseLLMProvider,
    ):
        uow = UnitOfWork()
        try:
            async with uow:
                retriever = Retriever()
                try:
                    retrieved_chunks = await retriever.hybrid_search(
                        session=uow.session,
                        query=user_message,
                        workspace_id=workspace_id,
                        limit=5,
                    )
                except Exception:  # noqa: BLE001
                    retrieved_chunks = []

                if retrieved_chunks:
                    doc_ids = list(
                        {
                            chunk.get("document_id")
                            for chunk in retrieved_chunks
                            if chunk.get("document_id")
                        }
                    )
                    if doc_ids:
                        stmt = select(Document.id).where(
                            Document.id.in_(doc_ids), Document.is_enabled == False
                        )
                        result = await uow.session.execute(stmt)
                        disabled_doc_ids = set(result.scalars().all())

                        if disabled_doc_ids:
                            retrieved_chunks = [
                                c
                                for c in retrieved_chunks
                                if c.get("document_id") not in disabled_doc_ids
                            ]

                system_prompt = (
                    "You are a helpful AI assistant. Answer questions based on the provided context if applicable. "
                    "If the context does not contain the answer and the user is asking a factual query, respond with: "
                    "'I do not have enough information in the provided documents to answer this request.' "
                    "However, you may answer conversational queries and refer to chat history normally."
                )
                context_builder = ContextBuilder(llm_provider)
                final_messages, accepted_chunks, metrics = (
                    context_builder.build_context(
                        system_prompt=system_prompt,
                        user_query=user_message,
                        retrieved_chunks=retrieved_chunks,
                        model_name=model_name,
                        chat_history=chat_history,
                    )
                )

                if accepted_chunks:
                    sources_data = [
                        {
                            "content": c.get("text"),
                            "document_name": c.get("document_name"),
                            "similarity_score": c.get("score"),
                            "image_url": c.get("metadata", {}).get("image_url", ""),
                        }
                        for c in accepted_chunks
                    ]
                    event_str = f"event: sources\ndata: {json.dumps(sources_data)}\n\n"
                    await queue.put(event_str)
                    await stream_manager.push_event(assistant_msg_id, event_str)
                else:
                    sources_data = []

                start_time = time.time()
                assistant_content = ""

                mcm = ModelCapabilityManager(uow.session)
                cap = await mcm.get_or_create_profile(provider_id, model_name)

                if cap.capability_state == "Unknown" or cap.capability_state == "Stale":
                    discovery_service = DiscoveryService(uow.session)
                    cap = await discovery_service.run_discovery(
                        provider_id, model_name, llm_provider.stream
                    )

                raw_kwargs = {
                    "prompt": user_message,
                    "messages": final_messages,
                    "system_prompt": system_prompt,
                    "model": model_name,
                    "temperature": 0.7,
                }

                safe_kwargs = mcm.filter_kwargs(raw_kwargs, cap)

                try:
                    original_stream_gen = llm_provider.stream(**safe_kwargs)
                    first_chunk = await builtins.anext(original_stream_gen)

                    async def _yield_rest():
                        yield first_chunk
                        while True:
                            try:
                                chunk = await builtins.anext(original_stream_gen)
                                yield chunk
                            except StopAsyncIteration:
                                break

                    stream_gen = _yield_rest()
                except StopAsyncIteration:

                    async def _empty():
                        yield ""

                    stream_gen = _empty()
                except Exception as e:
                    error_msg = str(e)
                    removed_param = _extract_unsupported_param(error_msg, safe_kwargs)
                    if removed_param:
                        logger.warning(
                            f"Unexpected unsupported parameter '{removed_param}' for {model_name}. Marking as Stale and retrying."
                        )
                        await mcm.mark_stale_and_update(cap, removed_param)
                        safe_kwargs = mcm.filter_kwargs(raw_kwargs, cap)
                        stream_gen = llm_provider.stream(**safe_kwargs)
                    else:
                        raise

                stmt = (
                    update(Message)
                    .where(Message.id == assistant_msg_id)
                    .values(status="generating")
                )
                await uow.session.execute(stmt)
                await uow.commit()

                async for chunk in stream_gen:
                    assistant_content += chunk
                    event_str = f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"
                    await queue.put(event_str)
                    await stream_manager.push_event(assistant_msg_id, event_str)

                latency_ms = (time.time() - start_time) * 1000
                completion_tokens = llm_provider.count_tokens(assistant_content)
                prompt_tokens = metrics.get(
                    "prompt_tokens", metrics.get("context_used", 0)
                )
                total_tokens = prompt_tokens + completion_tokens

                final_stats = {
                    "latency_ms": latency_ms,
                    "provider": provider_id,
                    "model": model_name,
                    "retrieved_chunks": len(accepted_chunks),
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "context_limit": metrics.get("context_limit", 128000),
                }
                stats_str = f"event: stats\ndata: {json.dumps(final_stats)}\n\n"
                await queue.put(stats_str)
                await stream_manager.push_event(assistant_msg_id, stats_str)

                done_str = "event: done\ndata: {}\n\n"
                await queue.put(done_str)
                await stream_manager.push_event(assistant_msg_id, done_str)

                stmt = (
                    update(Message)
                    .where(Message.id == assistant_msg_id)
                    .values(
                        status="completed",
                        content=assistant_content,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        model_id=model_name,
                        latency_ms=latency_ms,
                        sources_json=(
                            _json.dumps(sources_data) if sources_data else None
                        ),
                        completed_at=datetime.now(UTC),
                    )
                )
                await uow.session.execute(stmt)
                await uow.commit()

        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            try:
                error_str = str(e)
                event_str = (
                    f"event: error\ndata: {json.dumps({'message': error_str})}\n\n"
                )
                await queue.put(event_str)
                await stream_manager.push_event(assistant_msg_id, event_str)

                async with UnitOfWork() as error_uow:
                    stmt = (
                        update(Message)
                        .where(Message.id == assistant_msg_id)
                        .values(
                            status="failed",
                            error_message=error_str,
                            completed_at=datetime.now(UTC),
                        )
                    )
                    await error_uow.session.execute(stmt)
                    await error_uow.commit()
            except Exception:  # noqa: BLE001  # best-effort error recovery; don't shadow original exception
                logger.debug("Error recovery handler failed; original error already logged.")
        finally:
            await queue.put(None)
            await stream_manager.finish_stream(assistant_msg_id)
