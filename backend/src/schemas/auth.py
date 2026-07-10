from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_field(v)


def _validate_password_field(v: str) -> str:
    if not any(char.isdigit() for char in v):
        raise ValueError("Password must contain at least one digit")
    if not any(char.isupper() for char in v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(char.islower() for char in v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(char in "!@#$%^&*()-_=+[]{}|;:'\",.<>/?`~" for char in v):
        raise ValueError("Password must contain at least one special character")
    return v


class CreateWorkspaceRequest(BaseModel):
    workspace_name: str = Field(..., min_length=2, max_length=255)


class JoinWorkspaceRequest(BaseModel):
    join_code: str = Field(..., min_length=3, max_length=20)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class ResendOtpRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_field(v)


class Workspace(BaseModel):
    id: str
    name: str
    join_code: str | None = None
    is_owner: bool = False

    class Config:
        from_attributes = True
