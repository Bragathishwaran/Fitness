"""Authentication and profile business logic."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import PasswordChange, UserCreate, UserUpdate


def get_user_by_email(db: Session, email: str) -> User | None:
    """Find a user by case-insensitive email."""
    return db.scalar(select(User).where(func.lower(User.email) == email.lower()))


def get_user_by_username(db: Session, username: str) -> User | None:
    """Find a user by case-insensitive username."""
    return db.scalar(select(User).where(func.lower(User.username) == username.lower()))


def register_user(db: Session, payload: UserCreate) -> User:
    """Create a new user after validating email uniqueness."""
    if get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        username=payload.username.strip(),
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from None
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Validate credentials and return the matching user."""
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def build_token(user: User) -> str:
    """Create an access token for a user."""
    return create_access_token(user.id)


def update_profile(db: Session, user: User, payload: UserUpdate) -> User:
    """Update username/email with uniqueness validation."""
    if payload.email is not None:
        new_email = payload.email.lower()
        existing = get_user_by_email(db, new_email)
        if existing and existing.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )
        user.email = new_email

    if payload.username is not None:
        user.username = payload.username.strip()

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from None
    db.refresh(user)
    return user


def change_password(db: Session, user: User, payload: PasswordChange) -> None:
    """Change a user's password after verifying the current one."""
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
