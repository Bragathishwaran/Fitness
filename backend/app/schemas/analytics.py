"""Pydantic schemas for analytics and dashboard responses."""

from datetime import date

from pydantic import BaseModel

from app.schemas.goal import GoalOut
from app.schemas.workout import WorkoutOut


class ActivityPoint(BaseModel):
    """Workout activity aggregated for one day."""

    date: date
    workouts: int
    calories: int
    duration: int


class WeeklyPoint(BaseModel):
    """Workout activity aggregated for one week."""

    week_start: date
    week_end: date
    label: str
    workouts: int
    calories: int
    duration: int


class MonthlyPoint(BaseModel):
    """Workout activity aggregated for one month."""

    month: str
    label: str
    workouts: int
    calories: int
    duration: int


class CategoryPoint(BaseModel):
    """Workout distribution for one category."""

    category: str
    workouts: int
    calories: int
    percentage: float


class DashboardStats(BaseModel):
    """High-level numbers shown on the dashboard."""

    total_workouts: int
    total_calories: int
    total_duration: int
    active_goals: int
    completed_goals: int
    workouts_this_week: int
    calories_this_week: int
    current_streak: int


class DashboardOut(BaseModel):
    """Everything the dashboard needs in one response."""

    stats: DashboardStats
    weekly_activity: list[ActivityPoint]
    category_distribution: list[CategoryPoint]
    recent_workouts: list[WorkoutOut]
    goal_overview: list[GoalOut]


class AnalyticsTotals(BaseModel):
    """Totals for a custom analytics date range."""

    total_workouts: int
    total_calories: int
    total_duration: int
    average_duration: float
    average_calories: float
    active_days: int
    workouts_per_week: float


class AnalyticsOverview(BaseModel):
    """Analytics payload for a custom date range."""

    start_date: date
    end_date: date
    totals: AnalyticsTotals
    daily_activity: list[ActivityPoint]
    category_distribution: list[CategoryPoint]
    top_category: str | None


class FrequencyOut(BaseModel):
    """Workout frequency statistics."""

    days: int
    total_workouts: int
    active_days: int
    average_per_day: float
    average_per_week: float
    current_streak: int
