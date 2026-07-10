from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks
from typing import List, Optional
import os
from src.core.config import settings
from src.core.exceptions import ForbiddenError, NotFoundError
from src.schemas.document import DocumentResponse, DocumentToggleRequest
from src.services.document_service import DocumentService
from src.database.uow import UnitOfWork
from src.api.dependencies import get_uow, get_current_user, get_storage_provider
from src.providers.storage.base import BaseStorageProvider
from src.models.auth import User
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    uow: UnitOfWork = Depends(get_uow),
    storage: BaseStorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
):
    service = DocumentService(uow, storage)
    return await service.list_documents(current_user.workspace_id)


@router.post("/", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    uow: UnitOfWork = Depends(get_uow),
    storage: BaseStorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
):
    service = DocumentService(uow, storage)
    return await service.upload_document(
        file=file.file,
        filename=file.filename,
        mime_type=file.content_type,
        workspace_id=current_user.workspace_id,
        actor=current_user,
        background_tasks=background_tasks,
    )


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    uow: UnitOfWork = Depends(get_uow),
    storage: BaseStorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
):
    service = DocumentService(uow, storage)
    await service.delete_document(doc_id, current_user.workspace_id, current_user)
    return {"status": "deleted"}


@router.patch("/{doc_id}")
async def toggle_document(
    doc_id: str,
    data: DocumentToggleRequest,
    uow: UnitOfWork = Depends(get_uow),
    storage: BaseStorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
):
    service = DocumentService(uow, storage)
    await service.toggle_document(
        doc_id, current_user.workspace_id, current_user, data.is_enabled
    )
    return {"status": "success", "is_enabled": data.is_enabled}


@router.get("/media/{workspace_id}/{filename}")
async def get_media(
    workspace_id: str,
    filename: str,
    storage: BaseStorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
):

    if current_user.workspace_id != workspace_id:
        raise ForbiddenError("You do not have access to this workspace's media.")

    path = os.path.join(settings.upload_dir, workspace_id, filename)

    try:

        async def stream():
            async for chunk in storage.get_stream(path):
                yield chunk

        ext = filename.lower().split(".")[-1]
        media_type = "image/jpeg"
        if ext == "png":
            media_type = "image/png"

        return StreamingResponse(stream(), media_type=media_type)
    except FileNotFoundError:
        raise NotFoundError("Image", filename)
