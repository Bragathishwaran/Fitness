"""Pydantic schemas for notifications."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

NotificationKind = Literal["general", "daily_reminder", "goal_progress", "goal_completed"]


class NotificationCreate(BaseModel):
    """Internal payload for creating a notification."""

    title: str = Field(min_length=1, max_length=150)
    message: str = Field(min_length=1, max_length=500)
    kind: NotificationKind = "general"
    reference_id: int | None = None


class NotificationOut(BaseModel):
    """Notification returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    message: str
    kind: str
    reference_id: int | None
    is_read: bool
    created_at: datetime


class NotificationList(BaseModel):
    """Notification collection with unread count."""

    items: list[NotificationOut]
    total: int
    unread_count: int


class UnreadCount(BaseModel):
    """Unread notification count."""

    unread_count: int
