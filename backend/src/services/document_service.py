import hashlib
from typing import List, BinaryIO
from fastapi import BackgroundTasks
from src.core.exceptions import NotFoundError, ForbiddenError
from src.database.uow import UnitOfWork
from src.database.repositories.knowledge import DocumentRepository
from src.providers.storage.base import BaseStorageProvider
from src.models.knowledge import Document
from src.schemas.document import DocumentResponse
from sqlalchemy import select
from src.models.auth import User
from src.services.ingestion_service import IngestionService
from src.database.session import AsyncSessionLocal
from src.core.config import settings


class DocumentService:
    def __init__(self, uow: UnitOfWork, storage: BaseStorageProvider):
        self.uow = uow
        self.storage = storage

    async def list_documents(self, workspace_id: str) -> List[DocumentResponse]:
        async with self.uow:

            stmt = (
                select(Document, User.full_name.label("uploader_name"))
                .outerjoin(User, Document.uploaded_by == User.id)
                .where(Document.workspace_id == workspace_id)
            )

            result = await self.uow.session.execute(stmt)
            rows = result.all()

            return [
                DocumentResponse(
                    id=row.Document.id,
                    workspace_id=row.Document.workspace_id,
                    name=row.Document.name,
                    original_filename=row.Document.original_filename,
                    file_type=row.Document.mime_type,
                    file_size=row.Document.file_size,
                    status=row.Document.status,
                    error_message=row.Document.error_message,
                    is_enabled=getattr(row.Document, "is_enabled", True),
                    chunk_count=0,
                    version=1,
                    created_by=row.Document.uploaded_by,
                    uploader_name=row.uploader_name,
                    created_at=row.Document.created_at,
                    updated_at=row.Document.updated_at,
                )
                for row in rows
            ]

    async def upload_document(
        self,
        file: BinaryIO,
        filename: str,
        mime_type: str,
        workspace_id: str,
        actor: User,
        background_tasks: BackgroundTasks,
    ) -> DocumentResponse:

        file.seek(0)
        hasher = hashlib.sha256()
        while chunk := file.read(8192):
            hasher.update(chunk)
        file_hash = hasher.hexdigest()

        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)

        async with self.uow:
            doc_repo = DocumentRepository(self.uow.session)
            existing_doc = await doc_repo.get_by_hash_and_workspace(
                file_hash, workspace_id
            )
            if existing_doc:
                from src.core.exceptions import BadRequestError

                raise BadRequestError(
                    "A document with this content already exists in the workspace."
                )
        storage_path = await self.storage.upload_file(file, filename, workspace_id)

        async with self.uow:
            doc_repo = DocumentRepository(self.uow.session)
            doc = doc_repo.add(
                Document(
                    workspace_id=workspace_id,
                    name=filename,
                    original_filename=filename,
                    mime_type=mime_type,
                    file_size=file_size,
                    storage_path=storage_path,
                    status="pending",
                    file_hash=file_hash,
                    uploaded_by=actor.id,
                )
            )
            await self.uow.flush()
            await self.uow.commit()

            async def run_ingestion_task(
                doc_id: str, ws_id: str, storage_provider: BaseStorageProvider
            ):
                async with AsyncSessionLocal() as session:
                    repo = DocumentRepository(session)
                    document = await repo.get(doc_id)
                    if document:
                        svc = IngestionService()
                        await svc.ingest(
                            session,
                            document,
                            ws_id,
                            storage_provider,
                            settings.image_open_api_key,
                            settings.image_processing_model,
                        )
                        await session.commit()

            background_tasks.add_task(
                run_ingestion_task, doc.id, workspace_id, self.storage
            )

            return DocumentResponse(
                id=doc.id,
                workspace_id=doc.workspace_id,
                name=doc.name,
                original_filename=doc.original_filename,
                file_type=doc.mime_type,
                file_size=doc.file_size,
                status=doc.status,
                error_message=doc.error_message,
                is_enabled=getattr(doc, "is_enabled", True),
                chunk_count=0,
                version=1,
                created_by=doc.uploaded_by,
                uploader_name=actor.full_name,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )

    async def delete_document(
        self, doc_id: str, workspace_id: str, actor: User
    ) -> None:
        async with self.uow:
            doc_repo = DocumentRepository(self.uow.session)
            doc = await doc_repo.get(doc_id)

            if not doc or doc.workspace_id != workspace_id:
                raise NotFoundError("Document", doc_id)

            if doc.uploaded_by != actor.id and not getattr(actor, "is_owner", False):
                raise ForbiddenError("You can only delete your own documents.")

            storage_path = doc.storage_path

            await doc_repo.delete(doc_id)
            await self.uow.commit()
        try:
            await self.storage.delete_file(storage_path)
        except Exception:
            pass

    async def toggle_document(
        self, doc_id: str, workspace_id: str, actor: User, is_enabled: bool
    ) -> None:
        async with self.uow:
            doc_repo = DocumentRepository(self.uow.session)
            doc = await doc_repo.get(doc_id)

            if not doc or doc.workspace_id != workspace_id:
                raise NotFoundError("Document", doc_id)

            if not getattr(actor, "is_owner", False) and doc.uploaded_by != actor.id:
                raise ForbiddenError(
                    "You can only modify your own documents or need higher permissions."
                )

            doc.is_enabled = is_enabled
            await self.uow.commit()
