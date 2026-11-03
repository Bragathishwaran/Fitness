"""Notification routes."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationList, NotificationOut, UnreadCount
from app.services import notification_service
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationList, summary="List notifications")
def list_notifications(
    unread_only: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationList:
    items, total, unread_count = notification_service.list_notifications(
        db,
        current_user.id,
        unread_only=unread_only,
        skip=skip,
        limit=limit,
    )
    return NotificationList(items=items, total=total, unread_count=unread_count)


@router.get(
    "/unread-count",
    response_model=UnreadCount,
    summary="Get unread notification count",
)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnreadCount:
    return UnreadCount(
        unread_count=notification_service.get_unread_count(db, current_user.id)
    )


@router.post(
    "/read-all",
    summary="Mark all notifications as read",
)
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    updated = notification_service.mark_all_read(db, current_user.id)
    return {"updated": updated}


@router.post(
    "/{notification_id}/read",
    response_model=NotificationOut,
    summary="Mark one notification as read",
    responses={404: {"description": "Notification not found"}},
)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Notification:
    return notification_service.mark_read(db, current_user.id, notification_id)


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a notification",
    responses={404: {"description": "Notification not found"}},
)
def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    notification_service.delete_notification(db, current_user.id, notification_id)
