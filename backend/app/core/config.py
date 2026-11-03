"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings.

    Values are read from environment variables or a local ``.env`` file.
    Never commit real secrets to source control.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = "FitTrack API"
    API_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security -------------------------------------------------------------
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database -------------------------------------------------------------
    # PostgreSQL is recommended in production. The SQLite default keeps the
    # project runnable out of the box for a local demo.
    DATABASE_URL: str = "sqlite:///./fittrack.db"
    SQL_ECHO: bool = False
    AUTO_CREATE_TABLES: bool = True

    # CORS ----------------------------------------------------------------
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    # Scheduler -----------------------------------------------------------
    ENABLE_SCHEDULER: bool = True
    REMINDER_HOUR: int = 18
    REMINDER_MINUTE: int = 0

    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a clean list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()


settings = get_settings()
