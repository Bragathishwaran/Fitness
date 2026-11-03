"""Authentication and profile routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import (
    PasswordChange,
    Token,
    UserCreate,
    UserLogin,
    UserOut,
    UserUpdate,
)
from app.services import auth_service
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
    description="Create a user with a unique email and receive a JWT access token.",
    responses={409: {"description": "Email already registered"}},
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> Token:
    user = auth_service.register_user(db, payload)
    return Token(access_token=auth_service.build_token(user), user=user)


@router.post(
    "/login",
    response_model=Token,
    summary="Log in",
    description="Authenticate with email and password to receive a JWT access token.",
    responses={401: {"description": "Incorrect email or password"}},
)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    user = auth_service.authenticate_user(db, payload.email, payload.password)
    return Token(access_token=auth_service.build_token(user), user=user)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get the current user",
    responses={401: {"description": "Not authenticated"}},
)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.put(
    "/me",
    response_model=UserOut,
    summary="Update the current user's profile",
    responses={409: {"description": "Email already registered"}},
)
def update_current_user(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    return auth_service.update_profile(db, current_user, payload)


@router.put(
    "/me/password",
    summary="Change the current user's password",
    responses={400: {"description": "Current password is incorrect"}},
)
def change_current_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    auth_service.change_password(db, current_user, payload)
    return {"message": "Password updated successfully"}
