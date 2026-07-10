from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.core.exceptions import UnauthorizedError
from src.core.security import decode_token
from src.database.uow import UnitOfWork
from src.database.repositories.auth import UserRepository
from src.models.auth import User
from src.providers.storage.base import BaseStorageProvider
from src.providers.storage.local import LocalStorageProvider
from src.providers.llm.factory import get_provider
from src.models.auth import WorkspaceMember
from sqlalchemy import select

security = HTTPBearer()


def get_uow() -> UnitOfWork:
    return UnitOfWork()


def get_service(service_class):
    def _get_service(uow: UnitOfWork = Depends(get_uow)):
        return service_class(uow)

    return _get_service


def get_storage_provider() -> BaseStorageProvider:
    return LocalStorageProvider()


def get_llm_factory():
    return get_provider


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    uow: UnitOfWork = Depends(get_uow),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        workspace_id = payload.get("org")

        if not user_id:
            raise UnauthorizedError("Invalid token payload")

        async with uow:
            user_repo = UserRepository(uow.session)
            user = await user_repo.get(user_id)
            if not user or not user.is_active:
                raise UnauthorizedError("User not found or inactive")

            if workspace_id:
                stmt = select(WorkspaceMember).where(
                    WorkspaceMember.user_id == user.id,
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.deleted_at.is_(None),
                )
                member = (await uow.session.execute(stmt)).scalars().first()
                if not member:
                    raise UnauthorizedError("User not a member of this workspace")
                user.workspace_id = (
                    workspace_id
                )
                user.is_owner = member.is_owner
            else:
                user.workspace_id = None
                user.is_owner = False

            return user
    except Exception as e:
        raise UnauthorizedError(str(e))
