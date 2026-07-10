from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from src.schemas.chat import ChatRequest
from src.services.chat_service import ChatService
from src.database.uow import UnitOfWork
from src.api.dependencies import get_uow, get_current_user, get_llm_factory
from src.models.auth import User

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/{conversation_id}/stream")
async def stream_chat(
    conversation_id: str,
    data: ChatRequest,
    request: Request,
    uow: UnitOfWork = Depends(get_uow),
    llm_factory=Depends(get_llm_factory),
    current_user: User = Depends(get_current_user),
):
    service = ChatService(uow, llm_factory)

    return StreamingResponse(
        service.stream_chat(
            conversation_id, data, current_user.workspace_id, current_user, request
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{conversation_id}/messages/{message_id}/status")
async def get_message_status(
    conversation_id: str,
    message_id: str,
    uow: UnitOfWork = Depends(get_uow),
    llm_factory=Depends(get_llm_factory),
    current_user: User = Depends(get_current_user),
):
    service = ChatService(uow, llm_factory)
    return await service.get_message_status(
        conversation_id, message_id, current_user.workspace_id, current_user
    )


@router.get("/{conversation_id}/messages/{message_id}/stream")
async def stream_existing_message(
    conversation_id: str,
    message_id: str,
    request: Request,
    uow: UnitOfWork = Depends(get_uow),
    llm_factory=Depends(get_llm_factory),
    current_user: User = Depends(get_current_user),
):
    service = ChatService(uow, llm_factory)
    return StreamingResponse(
        service.stream_existing_message(
            conversation_id,
            message_id,
            current_user.workspace_id,
            current_user,
            request,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
