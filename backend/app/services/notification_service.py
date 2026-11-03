"""Notification creation, management and scheduled reminders."""

from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.notification import Notification
from app.models.user import User
from app.models.workout import Workout
from app.schemas.goal import calculate_completion_percentage
from app.schemas.notification import NotificationCreate
from app.utils.time import today_utc, utcnow


def create_notification(
    db: Session, user_id: int, payload: NotificationCreate
) -> Notification:
    """Add a notification to the session (caller commits)."""
    notification = Notification(
        user_id=user_id,
        title=payload.title,
        message=payload.message,
        kind=payload.kind,
        reference_id=payload.reference_id,
    )
    db.add(notification)
    db.flush()
    return notification


def notify_goal_change(
    db: Session,
    goal: Goal,
    previous_percentage: float,
    previous_status: str,
) -> None:
    """Create goal alerts when progress crosses meaningful thresholds.

    Alerts are deduplicated per goal and notification kind so that repeatedly
    editing a goal does not spam the user.
    """
    percentage = calculate_completion_percentage(goal.current_value, goal.target_value)

    if goal.status == "completed" and previous_status != "completed":
        if not _goal_alert_exists(db, goal, "goal_completed"):
            create_notification(
                db,
                goal.user_id,
                NotificationCreate(
                    title="Goal completed!",
                    message=f'Congratulations! You reached your {goal.goal_type} goal.',
                    kind="goal_completed",
                    reference_id=goal.id,
                ),
            )
        return

    if goal.status == "overdue" and previous_status != "overdue":
        if not _goal_alert_exists(db, goal, "goal_progress"):
            create_notification(
                db,
                goal.user_id,
                NotificationCreate(
                    title="Goal deadline passed",
                    message=(
                        f'Your {goal.goal_type} goal passed its deadline at '
                        f"{percentage:.0f}% completion. Update it or set a new goal."
                    ),
                    kind="goal_progress",
                    reference_id=goal.id,
                ),
            )
        return

    if percentage >= 75 and previous_percentage < 75:
        if not _goal_alert_exists(db, goal, "goal_progress"):
            create_notification(
                db,
                goal.user_id,
                NotificationCreate(
                    title="You are close to your goal",
                    message=(
                        f'Your {goal.goal_type} goal is {percentage:.0f}% complete. '
                        "Keep going!"
                    ),
                    kind="goal_progress",
                    reference_id=goal.id,
                ),
            )


def _goal_alert_exists(db: Session, goal: Goal, kind: str) -> bool:
    """Check whether an alert of this kind already exists for the goal."""
    return (
        db.scalar(
            select(Notification.id).where(
                Notification.user_id == goal.user_id,
                Notification.kind == kind,
                Notification.reference_id == goal.id,
            )
        )
        is not None
    )


def list_notifications(
    db: Session,
    user_id: int,
    *,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Notification], int, int]:
    """Return notifications, total count and unread count."""
    filters = [Notification.user_id == user_id]
    if unread_only:
        filters.append(Notification.is_read.is_(False))

    total = db.scalar(select(func.count(Notification.id)).where(*filters)) or 0
    unread_count = (
        db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        or 0
    )
    items = list(
        db.scalars(
            select(Notification)
            .where(*filters)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(skip)
            .limit(limit)
        )
    )
    return items, int(total), int(unread_count)


def get_unread_count(db: Session, user_id: int) -> int:
    """Return the number of unread notifications."""
    return (
        db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        or 0
    )


def mark_read(db: Session, user_id: int, notification_id: int) -> Notification:
    """Mark one owned notification as read."""
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, user_id: int) -> int:
    """Mark every unread notification as read. Returns affected count."""
    notifications = list(
        db.scalars(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
    )
    for notification in notifications:
        notification.is_read = True
    db.commit()
    return len(notifications)


def delete_notification(db: Session, user_id: int, notification_id: int) -> None:
    """Delete an owned notification."""
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    db.delete(notification)
    db.commit()


def generate_daily_reminders(db: Session) -> int:
    """Create one workout reminder per user per day.

    Users who already logged a workout today are skipped. An existing
    reminder created today prevents duplicates even if the job runs twice.
    """
    today = today_utc()
    start_of_day = datetime.combine(today, datetime.min.time())
    created = 0

    user_ids = list(db.scalars(select(User.id)))
    for user_id in user_ids:
        has_workout = (
            db.scalar(
                select(Workout.id).where(
                    Workout.user_id == user_id,
                    Workout.workout_date == today,
                )
            )
            is not None
        )
        if has_workout:
            continue

        reminder_exists = (
            db.scalar(
                select(Notification.id).where(
                    Notification.user_id == user_id,
                    Notification.kind == "daily_reminder",
                    Notification.created_at >= start_of_day,
                )
            )
            is not None
        )
        if reminder_exists:
            continue

        create_notification(
            db,
            user_id,
            NotificationCreate(
                title="Daily workout reminder",
                message="You have not logged a workout today. A short session still counts!",
                kind="daily_reminder",
            ),
        )
        created += 1

    db.commit()
    return created


def generate_goal_deadline_alerts(db: Session) -> int:
    """Alert users about active goals due within the next three days."""
    today = today_utc()
    start_of_day = datetime.combine(today, datetime.min.time())
    upcoming = today + timedelta(days=3)
    created = 0

    goals = list(
        db.scalars(
            select(Goal).where(
                Goal.status == "active",
                Goal.deadline >= today,
                Goal.deadline <= upcoming,
            )
        )
    )
    for goal in goals:
        alert_exists = (
            db.scalar(
                select(Notification.id).where(
                    Notification.user_id == goal.user_id,
                    Notification.kind == "goal_progress",
                    Notification.reference_id == goal.id,
                    Notification.created_at >= start_of_day,
                )
            )
            is not None
        )
        if alert_exists:
            continue

        percentage = calculate_completion_percentage(goal.current_value, goal.target_value)
        days_left = (goal.deadline - today).days
        deadline_text = "today" if days_left == 0 else f"in {days_left} day(s)"
        create_notification(
            db,
            goal.user_id,
            NotificationCreate(
                title="Goal deadline approaching",
                message=(
                    f'Your {goal.goal_type} goal is due {deadline_text} and is '
                    f"{percentage:.0f}% complete."
                ),
                kind="goal_progress",
                reference_id=goal.id,
            ),
        )
        created += 1

    db.commit()
    return created


def run_daily_jobs(db: Session) -> dict:
    """Entry point used by the scheduler."""
    return {
        "reminders": generate_daily_reminders(db),
        "goal_alerts": generate_goal_deadline_alerts(db),
        "ran_at": utcnow().isoformat(),
    }
