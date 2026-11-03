"""Pydantic schemas for daily progress."""

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.schemas.workout import WorkoutOut


class DailyProgressOut(BaseModel):
    """Aggregated statistics for a single day."""

    model_config = ConfigDict(from_attributes=True)

    date: date
    total_workouts: int
    total_calories: int
    total_duration: int


class DailyProgressDetail(DailyProgressOut):
    """Daily statistics with the underlying workout list."""

    workouts: list[WorkoutOut] = []


class ProgressSummary(BaseModel):
    """Progress totals over a date range plus per-day rows."""

    start_date: date
    end_date: date
    total_workouts: int
    total_calories: int
    total_duration: int
    days: list[DailyProgressOut]
