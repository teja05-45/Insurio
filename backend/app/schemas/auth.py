"""Authentication request and response schemas."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PASSWORD_MIN_LENGTH = 10


def validate_password_strength(value: str) -> str:
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")
    if len(value) > 128:
        raise ValueError("Password must be at most 128 characters.")
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one number.")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = Field(default="", max_length=120)

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_password_strength(value)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return value.strip().lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return value.strip().lower()


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return value.strip().lower()


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_password_strength(value)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_password_strength(value)


class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)

    @field_validator("full_name")
    @classmethod
    def _name(cls, value: str) -> str:
        return value.strip()


class DeleteAccountRequest(BaseModel):
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    user_agent: str
    ip_address: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
