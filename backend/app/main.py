"""FitTrack FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import Base, engine
from app.core.scheduler import shutdown_scheduler, start_scheduler
from app.routers import analytics, auth, goals, notifications, progress, workouts

# Importing models registers all tables on Base.metadata.
import app.models  # noqa: F401,E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("fittrack")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Create tables (local convenience) and manage the scheduler."""
    if settings.AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables are ready")
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=(
        "REST API for FitTrack, a fitness and workout management platform. "
        "Authenticate with the `/api/auth/login` endpoint, then use the "
        "Authorize button with the returned bearer token."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return a readable validation message alongside the detailed errors."""
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = ".".join(str(part) for part in first.get("loc", [])[1:]) or "input"
    message = f"{field}: {first.get('msg', 'Invalid value')}"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": message, "errors": errors},
    )


api_routers = [
    auth.router,
    workouts.router,
    progress.router,
    goals.router,
    analytics.router,
    notifications.router,
]

for api_router in api_routers:
    app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/", tags=["Health"], summary="Service information")
def root() -> dict[str, str]:
    """Basic service metadata."""
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get(f"{settings.API_PREFIX}/health", tags=["Health"], summary="Health check")
def health_check() -> dict[str, str]:
    """Health check used by clients and deployment tooling."""
    return {"status": "ok"}
