"""Reports and analytics routes."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsOverview,
    CategoryPoint,
    DashboardOut,
    FrequencyOut,
    MonthlyPoint,
    WeeklyPoint,
)
from app.services import analytics_service
from app.utils.dependencies import get_current_user
from app.utils.time import today_utc

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/dashboard",
    response_model=DashboardOut,
    summary="Get dashboard data",
    description="All-time totals, weekly activity, category distribution, recent workouts and active goals.",
)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return analytics_service.get_dashboard(db, current_user.id)


@router.get(
    "/overview",
    response_model=AnalyticsOverview,
    summary="Get analytics overview for a date range",
    description="Defaults to the last 30 days.",
)
def get_overview(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    end = end_date or today_utc()
    start = start_date or (end - timedelta(days=29))
    return analytics_service.get_overview(db, current_user.id, start, end)


@router.get(
    "/weekly",
    response_model=list[WeeklyPoint],
    summary="Get weekly workout summary",
    description="Defaults to the last 8 weeks.",
)
def get_weekly_summary(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    end = end_date or today_utc()
    start = start_date or (end - timedelta(days=55))
    return analytics_service.get_weekly_summary(db, current_user.id, start, end)


@router.get(
    "/monthly",
    response_model=list[MonthlyPoint],
    summary="Get monthly workout summary",
    description="Returns the last N months (default 6).",
)
def get_monthly_summary(
    months: int = Query(default=6, ge=1, le=24),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return analytics_service.get_monthly_summary(db, current_user.id, months)


@router.get(
    "/categories",
    response_model=list[CategoryPoint],
    summary="Get workout category distribution",
)
def get_category_breakdown(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return analytics_service.get_category_breakdown(
        db, current_user.id, start_date, end_date
    )


@router.get(
    "/frequency",
    response_model=FrequencyOut,
    summary="Get workout frequency statistics",
)
def get_frequency(
    days: int = Query(default=30, ge=1, le=366),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return analytics_service.get_frequency(db, current_user.id, days)
