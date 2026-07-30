
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.repositories.base import BaseRepository
from src.models.knowledge import Document


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, session: AsyncSession):
        super().__init__(Document, session)

    async def list_by_org(self, workspace_id: str) -> list[Document]:
        stmt = select(Document).where(Document.workspace_id == workspace_id)
        stmt = stmt.order_by(Document.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_total_size(self, workspace_id: str) -> int:
        stmt = select(func.sum(Document.file_size)).where(
            Document.workspace_id == workspace_id
        )
        result = await self.session.execute(stmt)
        val = result.scalar()
        return val if val else 0

    async def get_by_hash_and_workspace(
        self, file_hash: str, workspace_id: str
    ) -> Document | None:
        stmt = select(Document).where(
            Document.file_hash == file_hash,
            Document.workspace_id == workspace_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
