"""Daily progress routes."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.progress import DailyProgressDetail, ProgressSummary
from app.services import progress_service
from app.utils.dependencies import get_current_user
from app.utils.time import today_utc

router = APIRouter(prefix="/progress", tags=["Progress"])


@router.get(
    "/daily",
    response_model=DailyProgressDetail,
    summary="Get daily progress",
    description="Returns live aggregated statistics and workouts for a selected date.",
)
def get_daily_progress(
    target_date: date | None = Query(default=None, alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    selected_date = target_date or today_utc()
    return progress_service.get_daily_detail(db, current_user.id, selected_date)


@router.get(
    "/history",
    response_model=ProgressSummary,
    summary="Get progress history",
    description="Returns per-day totals for a date range (defaults to the last 30 days).",
)
def get_progress_history(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    end = end_date or today_utc()
    start = start_date or (end - timedelta(days=29))
    return progress_service.get_summary(db, current_user.id, start, end)
