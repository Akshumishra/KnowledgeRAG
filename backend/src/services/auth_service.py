import random
import string
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from src.core.config import settings
from src.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from src.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from src.database.repositories.auth import UserRepository
from src.database.repositories.workspace import WorkspaceRepository
from src.database.uow import UnitOfWork
from src.models.auth import RefreshToken, User, WorkspaceMember
from src.models.workspace import Workspace
from src.schemas.auth import (
    CreateWorkspaceRequest,
    JoinWorkspaceRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from src.schemas.auth import Workspace as SchemaWorkspace


def _generate_join_code() -> str:
    """Generate a short, readable join code like ABC-1234."""
    letters = "".join(random.choices(string.ascii_uppercase, k=3))
    digits = "".join(random.choices(string.digits, k=4))
    return f"{letters}-{digits}"


def _slugify(name: str) -> str:
    """Convert a workspace name to a URL-safe slug."""
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return (
        slug[:50]
        + "-"
        + "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    )


from src.services.email_service import EmailService


def _generate_otp() -> str:
    """Generate a 6-digit numeric OTP."""
    return "".join(random.choices(string.digits, k=6))


class AuthService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.email_service = EmailService()

    async def register(self, data: RegisterRequest) -> tuple[User, None]:
        async with self.uow:
            user_repo = UserRepository(self.uow.session)

            if await user_repo.get_by_email(data.email):
                raise ConflictError(f"Email '{data.email}' is already registered.")

            otp = _generate_otp()
            expires_at = datetime.now(UTC) + timedelta(minutes=15)

            user = user_repo.add(
                User(
                    email=data.email.lower(),
                    full_name=data.full_name,
                    password_hash=hash_password(data.password),
                    is_active=True,
                    is_verified=False,
                    otp_code=otp,
                    otp_expires_at=expires_at,
                )
            )
            await self.uow.flush()

            self.email_service.send_email(
                user.email,
                "Verify your email",
                f"<p>Hello {user.full_name},</p><p>Your verification code is: <strong>{otp}</strong></p><p>It expires in 15 minutes.</p>",
            )

            await self.uow.commit()
            return user, None

    async def verify_email_otp(
        self, email: str, otp: str
    ) -> tuple[User, TokenResponse]:
        async with self.uow:
            user_repo = UserRepository(self.uow.session)
            user = await user_repo.get_by_email(email)
            if not user:
                raise NotFoundError("User not found")

            if user.is_verified:
                raise ConflictError("Email is already verified")

            if (
                user.otp_code != otp
                or not user.otp_expires_at
                or user.otp_expires_at < datetime.now(UTC)
            ):
                raise UnauthorizedError("Invalid or expired OTP")

            user.is_verified = True
            user.otp_code = None
            user.otp_expires_at = None
            user.last_login = datetime.now(UTC)

            tokens = await self._generate_tokens(user, workspace_id=None)
            await self.uow.commit()
            return user, tokens

    async def resend_otp(self, email: str) -> None:
        async with self.uow:
            user_repo = UserRepository(self.uow.session)
            user = await user_repo.get_by_email(email)
            if not user:
                return

            if user.is_verified:
                raise ConflictError("Email is already verified")

            otp = _generate_otp()
            user.otp_code = otp
            user.otp_expires_at = datetime.now(UTC) + timedelta(minutes=15)
            await self.uow.flush()

            self.email_service.send_email(
                user.email,
                "Verify your email",
                f"<p>Hello {user.full_name},</p><p>Your new verification code is: <strong>{otp}</strong></p><p>It expires in 15 minutes.</p>",
            )
            await self.uow.commit()

    async def process_forgot_password(self, email: str) -> None:
        async with self.uow:
            user_repo = UserRepository(self.uow.session)
            user = await user_repo.get_by_email(email)
            if not user:
                # Do not leak that user doesn't exist, just return
                return

            otp = _generate_otp()
            user.otp_code = otp
            user.otp_expires_at = datetime.now(UTC) + timedelta(minutes=15)
            await self.uow.flush()

            self.email_service.send_email(
                user.email,
                "Password Reset",
                f"<p>Hello {user.full_name},</p><p>Your password reset code is: <strong>{otp}</strong></p><p>It expires in 15 minutes.</p>",
            )
            await self.uow.commit()

    async def reset_password_with_otp(
        self, email: str, otp: str, new_password: str
    ) -> None:
        async with self.uow:
            user_repo = UserRepository(self.uow.session)
            user = await user_repo.get_by_email(email)
            if not user:
                raise UnauthorizedError("Invalid or expired OTP")

            if (
                user.otp_code != otp
                or not user.otp_expires_at
                or user.otp_expires_at < datetime.now(UTC)
            ):
                raise UnauthorizedError("Invalid or expired OTP")

            user.password_hash = hash_password(new_password)
            user.otp_code = None
            user.otp_expires_at = None
            await self.uow.commit()

    async def login(self, data: LoginRequest) -> tuple[User, TokenResponse]:
        async with self.uow:
            user_repo = UserRepository(self.uow.session)
            user = await user_repo.get_by_email(data.email)
            if not user or not verify_password(data.password, user.password_hash):
                raise UnauthorizedError("Invalid email or password")
            if not user.is_active:
                raise UnauthorizedError("Account is disabled")
            if not user.is_verified:
                raise UnauthorizedError(
                    "Email is not verified. Please verify your email first."
                )

            user.last_login = datetime.now(UTC)
            tokens = await self._generate_tokens(user, workspace_id=None)
            await self.uow.commit()
            return user, tokens

    async def get_workspaces(self, user: User) -> list[Workspace]:
        async with self.uow:
            stmt = (
                select(WorkspaceMember, Workspace)
                .join(Workspace, WorkspaceMember.workspace_id == Workspace.id)
                .where(
                    WorkspaceMember.user_id == user.id,
                    WorkspaceMember.deleted_at.is_(None),
                    Workspace.deleted_at.is_(None),
                )
            )

            result = await self.uow.session.execute(stmt)
            rows = result.all()

            workspaces = []
            for row in rows:
                member_obj = row.WorkspaceMember
                org = row.Workspace
                workspaces.append(
                    SchemaWorkspace(
                        id=org.id,
                        name=org.name,
                        join_code=org.join_code,
                        is_owner=member_obj.is_owner,
                    )
                )
            return workspaces

    async def create_workspace(
        self, data: CreateWorkspaceRequest, user: User
    ) -> tuple[Workspace, TokenResponse]:
        async with self.uow:
            org_repo = WorkspaceRepository(self.uow.session)
            slug = _slugify(data.workspace_name)
            join_code = _generate_join_code()
            while await org_repo.get_by_join_code(join_code):
                join_code = _generate_join_code()

            org = org_repo.add(
                Workspace(name=data.workspace_name, slug=slug, join_code=join_code)
            )
            await self.uow.flush()
            member = WorkspaceMember(
                user_id=user.id, workspace_id=org.id, is_owner=True
            )
            self.uow.session.add(member)
            await self.uow.flush()

            tokens = await self._generate_tokens(user, workspace_id=org.id)
            await self.uow.commit()
            return org, tokens

    async def join_workspace(
        self, data: JoinWorkspaceRequest, user: User
    ) -> tuple[Workspace, TokenResponse]:
        async with self.uow:
            org_repo = WorkspaceRepository(self.uow.session)

            org = await org_repo.get_by_join_code(data.join_code)
            if not org:
                raise NotFoundError("Workspace", data.join_code)
            stmt_check = select(WorkspaceMember).where(
                WorkspaceMember.user_id == user.id,
                WorkspaceMember.workspace_id == org.id,
                WorkspaceMember.deleted_at.is_(None),
            )
            if (await self.uow.session.execute(stmt_check)).first():
                raise ConflictError("You are already a member of this workspace.")
            member = WorkspaceMember(
                user_id=user.id, workspace_id=org.id, is_owner=False
            )
            self.uow.session.add(member)
            await self.uow.flush()

            tokens = await self._generate_tokens(user, workspace_id=org.id)
            await self.uow.commit()
            return org, tokens

    async def enter_workspace(self, workspace_id: str, user: User) -> TokenResponse:
        async with self.uow:
            stmt_check = select(WorkspaceMember).where(
                WorkspaceMember.user_id == user.id,
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.deleted_at.is_(None),
            )
            if not (await self.uow.session.execute(stmt_check)).first():
                raise UnauthorizedError("You are not a member of this workspace.")

            tokens = await self._generate_tokens(user, workspace_id=workspace_id)
            await self.uow.commit()
            return tokens

    async def refresh(self, refresh_token: str) -> TokenResponse:
        async with self.uow:
            stmt = (
                select(RefreshToken, User)
                .join(User)
                .where(
                    RefreshToken.token == refresh_token,
                    RefreshToken.is_revoked.is_(False),
                    RefreshToken.expires_at > datetime.now(UTC),
                )
            )
            result = await self.uow.session.execute(stmt)
            row = result.first()
            if not row:
                raise UnauthorizedError("Invalid or expired refresh token")

            rt, user = row
            rt.is_revoked = True
            tokens = await self._generate_tokens(user, workspace_id=None)
            await self.uow.commit()
            return tokens

    async def _generate_tokens(
        self, user: User, workspace_id: str | None
    ) -> TokenResponse:
        extra = {}
        if workspace_id:
            extra["org"] = workspace_id

        access_token = create_access_token(subject=user.id, extra=extra)
        refresh_token_str = create_refresh_token(subject=user.id)

        rt = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_expire_days),
        )
        self.uow.session.add(rt)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def delete_workspace(self, workspace_id: str, actor: User) -> None:
        async with self.uow:
            stmt_check = select(WorkspaceMember).where(
                WorkspaceMember.user_id == actor.id,
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.is_owner == True,
                WorkspaceMember.deleted_at.is_(None),
            )
            if not (await self.uow.session.execute(stmt_check)).first():
                raise ForbiddenError()

            org_repo = WorkspaceRepository(self.uow.session)
            org = await org_repo.get(workspace_id)
            if not org:
                raise NotFoundError("Workspace", workspace_id)

            stmt = (
                update(Workspace)
                .where(Workspace.id == workspace_id)
                .values(deleted_at=datetime.now(UTC))
            )
            await self.uow.session.execute(stmt)

            stmt_members = (
                update(WorkspaceMember)
                .where(WorkspaceMember.workspace_id == workspace_id)
                .values(deleted_at=datetime.now(UTC))
            )
            await self.uow.session.execute(stmt_members)

            await self.uow.commit()
