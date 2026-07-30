
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.repositories.base import BaseRepository
from src.models.workspace import Workspace, WorkspaceAPIKey


class WorkspaceRepository(BaseRepository[Workspace]):
    def __init__(self, session: AsyncSession):
        super().__init__(Workspace, session)

    async def get_by_slug(self, slug: str) -> Workspace | None:
        stmt = select(Workspace).where(Workspace.slug == slug.lower())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_join_code(self, join_code: str) -> Workspace | None:
        stmt = select(Workspace).where(Workspace.join_code == join_code.upper())
        result = await self.session.execute(stmt)
        return result.scalars().first()


class WorkspaceAPIKeyRepository(BaseRepository[WorkspaceAPIKey]):
    def __init__(self, session: AsyncSession):
        super().__init__(WorkspaceAPIKey, session)

    async def get_by_org_and_provider(
        self, workspace_id: str, provider_id: str
    ) -> WorkspaceAPIKey | None:
        stmt = select(WorkspaceAPIKey).where(
            WorkspaceAPIKey.workspace_id == workspace_id,
            WorkspaceAPIKey.provider_id == provider_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
