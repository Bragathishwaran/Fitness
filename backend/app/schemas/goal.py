"""Pydantic schemas for fitness goals."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

GoalType = Literal["Weight Loss", "Muscle Gain", "Steps"]


def calculate_completion_percentage(current_value: float, target_value: float) -> float:
    """Safely calculate completion percentage, avoiding division by zero."""
    if target_value <= 0:
        return 0.0
    percentage = (current_value / target_value) * 100
    return round(min(max(percentage, 0.0), 100.0), 2)


class GoalBase(BaseModel):
    """Shared goal fields."""

    goal_type: GoalType
    target_value: float = Field(gt=0, le=1_000_000)
    current_value: float = Field(default=0, ge=0, le=1_000_000)
    deadline: date


class GoalCreate(GoalBase):
    """Payload for creating a goal."""


class GoalUpdate(BaseModel):
    """Payload for editing a goal. All fields are optional."""

    goal_type: GoalType | None = None
    target_value: float | None = Field(default=None, gt=0, le=1_000_000)
    current_value: float | None = Field(default=None, ge=0, le=1_000_000)
    deadline: date | None = None


class GoalProgressUpdate(BaseModel):
    """Payload for updating the current progress value of a goal."""

    current_value: float = Field(ge=0, le=1_000_000)


class GoalOut(GoalBase):
    """Goal returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: Literal["active", "completed", "overdue"]
    created_at: datetime

    @computed_field
    @property
    def completion_percentage(self) -> float:
        return calculate_completion_percentage(self.current_value, self.target_value)


class GoalList(BaseModel):
    """Goal collection response with summary counts."""

    items: list[GoalOut]
    total: int
    active: int
    completed: int
    overdue: int
