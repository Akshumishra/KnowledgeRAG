from typing import List
from fastapi import APIRouter, Depends
from src.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    CreateWorkspaceRequest,
    JoinWorkspaceRequest,
    Workspace,
    RefreshRequest,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ResendOtpRequest,
)
from src.services.auth_service import AuthService
from src.database.uow import UnitOfWork
from src.api.dependencies import get_uow, get_current_user
from src.models.auth import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(data: RegisterRequest, uow: UnitOfWork = Depends(get_uow)):
    service = AuthService(uow)
    user, _ = await service.register(data)
    return {"message": "Verification email sent"}


@router.post("/verify-email", response_model=TokenResponse)
async def verify_email(data: VerifyEmailRequest, uow: UnitOfWork = Depends(get_uow)):
    service = AuthService(uow)
    user, tokens = await service.verify_email_otp(data.email, data.otp)
    return tokens


@router.post("/resend-otp")
async def resend_otp(data: ResendOtpRequest, uow: UnitOfWork = Depends(get_uow)):
    service = AuthService(uow)
    await service.resend_otp(data.email)
    return {
        "message": "If the email is registered and unverified, a new OTP has been sent."
    }


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest, uow: UnitOfWork = Depends(get_uow)
):
    service = AuthService(uow)
    await service.process_forgot_password(data.email)
    return {"message": "If the email is registered, a reset code has been sent."}


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest, uow: UnitOfWork = Depends(get_uow)
):
    service = AuthService(uow)
    await service.reset_password_with_otp(data.email, data.otp, data.new_password)
    return {"message": "Password has been successfully reset."}


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, uow: UnitOfWork = Depends(get_uow)):
    service = AuthService(uow)
    user, tokens = await service.login(data)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, uow: UnitOfWork = Depends(get_uow)):
    service = AuthService(uow)
    return await service.refresh(data.refresh_token)


@router.get("/workspaces", response_model=List[Workspace])
async def list_workspaces(
    uow: UnitOfWork = Depends(get_uow), current_user: User = Depends(get_current_user)
):
    service = AuthService(uow)
    return await service.get_workspaces(current_user)


@router.post("/workspaces")
async def create_workspace(
    data: CreateWorkspaceRequest,
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_user),
):
    service = AuthService(uow)
    org, tokens = await service.create_workspace(data, current_user)
    return {
        **tokens.model_dump(),
        "workspace_name": org.name,
        "join_code": org.join_code,
    }


@router.post("/workspaces/join")
async def join_workspace(
    data: JoinWorkspaceRequest,
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_user),
):
    service = AuthService(uow)
    org, tokens = await service.join_workspace(data, current_user)
    return {
        **tokens.model_dump(),
        "workspace_name": org.name,
        "join_code": org.join_code,
    }


@router.post("/workspaces/{workspace_id}/enter", response_model=TokenResponse)
async def enter_workspace(
    workspace_id: str,
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_user),
):
    service = AuthService(uow)
    return await service.enter_workspace(workspace_id, current_user)


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "workspace_id": getattr(current_user, "workspace_id", None),
        "is_owner": getattr(current_user, "is_owner", False),
    }


@router.delete("/workspaces/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: str,
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_user),
):
    service = AuthService(uow)
    await service.delete_workspace(workspace_id, current_user)
