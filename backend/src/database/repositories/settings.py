
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.repositories.base import BaseRepository
from src.models.settings import LLMProvider
from src.models.workspace import WorkspaceModel


class LLMProviderRepository(BaseRepository[LLMProvider]):
    def __init__(self, session: AsyncSession):
        super().__init__(LLMProvider, session)

    async def get_by_slug(self, slug: str) -> LLMProvider | None:
        stmt = select(LLMProvider).where(LLMProvider.slug == slug.lower())
        result = await self.session.execute(stmt)
        return result.scalars().first()


class WorkspaceModelRepository(BaseRepository[WorkspaceModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(WorkspaceModel, session)

    async def get_for_provider(
        self, workspace_id: str, provider_id: str
    ) -> list[WorkspaceModel]:
        stmt = select(WorkspaceModel).where(
            WorkspaceModel.workspace_id == workspace_id,
            WorkspaceModel.provider_id == provider_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_for_workspace(self, workspace_id: str) -> list[WorkspaceModel]:
        stmt = select(WorkspaceModel).where(WorkspaceModel.workspace_id == workspace_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_for_provider(self, workspace_id: str, provider_id: str) -> None:
        stmt = delete(WorkspaceModel).where(
            WorkspaceModel.workspace_id == workspace_id,
            WorkspaceModel.provider_id == provider_id,
        )
        await self.session.execute(stmt)
