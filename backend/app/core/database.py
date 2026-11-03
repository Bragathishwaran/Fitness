"""SQLAlchemy engine, session factory and declarative base."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _engine_options(database_url: str) -> dict:
    """Build engine options that work for SQLite and PostgreSQL."""
    options: dict = {"pool_pre_ping": True, "echo": settings.SQL_ECHO}
    if database_url.startswith("sqlite"):
        # SQLite needs this flag to share an in-memory database across threads
        # (used by the test suite) and to allow the same connection in requests.
        options["connect_args"] = {"check_same_thread": False}
    return options


def _database_url() -> str:
    """Keep the local SQLite database beside the backend regardless of cwd."""
    database_url = settings.DATABASE_URL
    if database_url == "sqlite:///./fittrack.db":
        database_path = Path(__file__).resolve().parents[2] / "fittrack.db"
        return f"sqlite:///{database_path.as_posix()}"
    return database_url


DATABASE_URL = _database_url()
engine = create_engine(DATABASE_URL, **_engine_options(DATABASE_URL))

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
