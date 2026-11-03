"""Pydantic schemas for workouts."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

WorkoutCategory = Literal["Cardio", "Strength", "Yoga"]


class WorkoutBase(BaseModel):
    """Shared workout fields."""

    workout_name: str = Field(min_length=2, max_length=120)
    category: WorkoutCategory
    duration: int = Field(ge=1, le=1440, description="Duration in minutes")
    calories_burned: int = Field(ge=0, le=20000)
    workout_date: date


class WorkoutCreate(WorkoutBase):
    """Payload for creating a workout."""


class WorkoutUpdate(BaseModel):
    """Payload for updating a workout. All fields are optional."""

    workout_name: str | None = Field(default=None, min_length=2, max_length=120)
    category: WorkoutCategory | None = None
    duration: int | None = Field(default=None, ge=1, le=1440)
    calories_burned: int | None = Field(default=None, ge=0, le=20000)
    workout_date: date | None = None


class WorkoutOut(WorkoutBase):
    """Workout returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime


class WorkoutList(BaseModel):
    """Paginated workout list response."""

    items: list[WorkoutOut]
    total: int
    skip: int
    limit: int
