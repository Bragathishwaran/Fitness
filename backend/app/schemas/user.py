"""Pydantic schemas for users and authentication."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 64


def validate_password_strength(value: str) -> str:
    """Ensure a password has a reasonable length and mixed characters."""
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long")
    if len(value) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"Password must be at most {PASSWORD_MAX_LENGTH} characters long")
    if not re.search(r"[A-Za-z]", value):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one number")
    return value


class UserBase(BaseModel):
    """Shared user fields."""

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9 _.-]+", value):
            raise ValueError(
                "Username may only contain letters, numbers, spaces, dots, underscores and hyphens"
            )
        return value


class UserCreate(UserBase):
    """Registration payload."""

    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class UserLogin(BaseModel):
    """Login payload."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class UserUpdate(BaseModel):
    """Profile update payload. All fields are optional."""

    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9 _.-]+", value):
            raise ValueError(
                "Username may only contain letters, numbers, spaces, dots, underscores and hyphens"
            )
        return value


class PasswordChange(BaseModel):
    """Password change payload."""

    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class UserOut(BaseModel):
    """Public user representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    """Authentication response with JWT and user profile."""

    access_token: str
    token_type: str = "bearer"
    user: UserOut
