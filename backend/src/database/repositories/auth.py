from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.repositories.base import BaseRepository
from src.models.auth import User, WorkspaceMember


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get(self, id: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(selectinload(User.workspaces))
            .where(User.id == id, User.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(selectinload(User.workspaces))
            .where(User.email == email.lower(), User.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active_users_in_org(self, workspace_id: str) -> list[User]:
        stmt = (
            select(User)
            .join(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.deleted_at.is_(None),
                User.is_active == True,
                User.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    def __init__(self, session: AsyncSession):
        super().__init__(WorkspaceMember, session)

    async def get_membership(
        self, user_id: str, workspace_id: str
    ) -> Optional[WorkspaceMember]:
        stmt = select(WorkspaceMember).where(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
