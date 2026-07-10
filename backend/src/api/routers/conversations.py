from fastapi import APIRouter, Depends
from typing import List
from src.schemas.chat import ConversationResponse, ConversationCreate, MessageResponse
from src.services.conversation_service import ConversationService
from src.api.dependencies import get_service, get_current_user
from src.models.auth import User

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    service: ConversationService = Depends(get_service(ConversationService)),
    current_user: User = Depends(get_current_user),
):
    return await service.list_conversations(current_user)


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    service: ConversationService = Depends(get_service(ConversationService)),
    current_user: User = Depends(get_current_user),
):
    return await service.create_conversation(data, current_user)


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_service(ConversationService)),
    current_user: User = Depends(get_current_user),
):
    return await service.get_conversation(conversation_id, current_user)


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    service: ConversationService = Depends(get_service(ConversationService)),
    current_user: User = Depends(get_current_user),
):
    return await service.get_messages(conversation_id, current_user)


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_service(ConversationService)),
    current_user: User = Depends(get_current_user),
):
    await service.delete_conversation(conversation_id, current_user)
