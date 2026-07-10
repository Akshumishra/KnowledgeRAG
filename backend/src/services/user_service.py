from typing import List
from src.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from src.database.uow import UnitOfWork
from src.database.repositories.auth import UserRepository
from src.models.auth import User
from src.models.auth import WorkspaceMember
from sqlalchemy import select, update
from datetime import datetime, timezone


class UserService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def list(self, workspace_id: str) -> List[User]:
        async with self.uow:
            user_repo = UserRepository(self.uow.session)
            return await user_repo.get_active_users_in_org(workspace_id)

    async def get(self, user_id: str, workspace_id: str) -> User:
        async with self.uow:
            user_repo = UserRepository(self.uow.session)
            user = await user_repo.get(user_id)
            if not user:
                raise NotFoundError("User", user_id)

            stmt = select(WorkspaceMember).where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.deleted_at.is_(None),
            )
            if not (await self.uow.session.execute(stmt)).first():
                raise NotFoundError("User", user_id)
            return user

    async def remove_from_workspace(
        self, user_id: str, workspace_id: str, actor: User
    ) -> None:
        if not getattr(actor, "is_owner", False):
            raise ForbiddenError()
        if user_id == actor.id:
            raise ConflictError(
                "You cannot remove yourself from the workspace. Use leave workspace instead."
            )

        async with self.uow:

            stmt = (
                update(WorkspaceMember)
                .where(
                    WorkspaceMember.user_id == user_id,
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.deleted_at.is_(None),
                )
                .values(deleted_at=datetime.now(timezone.utc))
            )
            result = await self.uow.session.execute(stmt)
            if result.rowcount == 0:
                raise NotFoundError("User not found in workspace", user_id)

            await self.uow.commit()

    async def get_activity(self, user_id: str):
        from src.models.auth import UserActivity
        async with self.uow:
            stmt = select(UserActivity).where(UserActivity.user_id == user_id)
            result = await self.uow.session.execute(stmt)
            activity = result.scalar_one_or_none()
            if not activity:
                activity = UserActivity(user_id=user_id, last_route="chat")
                self.uow.session.add(activity)
                await self.uow.commit()
            return activity

    async def update_activity(self, user_id: str, last_route: str, last_conversation_id: str = None):
        from src.models.auth import UserActivity
        async with self.uow:
            stmt = select(UserActivity).where(UserActivity.user_id == user_id)
            result = await self.uow.session.execute(stmt)
            activity = result.scalar_one_or_none()
            if activity:
                activity.last_route = last_route
                activity.last_conversation_id = last_conversation_id
            else:
                activity = UserActivity(
                    user_id=user_id,
                    last_route=last_route,
                    last_conversation_id=last_conversation_id,
                )
                self.uow.session.add(activity)
            await self.uow.commit()
            return activity

