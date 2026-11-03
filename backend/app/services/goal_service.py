"""Fitness goal business logic."""

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.user import User
from app.schemas.goal import (
    GoalCreate,
    GoalProgressUpdate,
    GoalUpdate,
    calculate_completion_percentage,
)
from app.services.notification_service import notify_goal_change
from app.utils.time import today_utc


def compute_status(goal: Goal, today: date | None = None) -> str:
    """Derive a goal's status from its values and deadline."""
    today = today or today_utc()
    if goal.current_value >= goal.target_value:
        return "completed"
    if goal.deadline < today:
        return "overdue"
    return "active"


def _refresh_goal_status(goal: Goal) -> bool:
    """Update the stored status. Returns True when it changed."""
    new_status = compute_status(goal)
    if goal.status != new_status:
        goal.status = new_status
        return True
    return False


def list_goals(db: Session, user_id: int) -> list[Goal]:
    """Return the user's goals, refreshing statuses first."""
    goals = list(
        db.scalars(
            select(Goal)
            .where(Goal.user_id == user_id)
            .order_by(Goal.deadline.asc(), Goal.id.desc())
        )
    )
    changed = False
    for goal in goals:
        changed = _refresh_goal_status(goal) or changed
    if changed:
        db.commit()
    return goals


def get_goal(db: Session, user_id: int, goal_id: int) -> Goal:
    """Fetch a goal and enforce ownership."""
    goal = db.get(Goal, goal_id)
    if not goal or goal.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        )
    return goal


def create_goal(db: Session, user: User, payload: GoalCreate) -> Goal:
    """Create a goal and derive its initial status."""
    goal = Goal(user_id=user.id, **payload.model_dump())
    goal.status = compute_status(goal)
    db.add(goal)
    db.flush()
    notify_goal_change(db, goal, 0.0, "active")
    db.commit()
    db.refresh(goal)
    return goal


def update_goal(
    db: Session, user: User, goal_id: int, payload: GoalUpdate
) -> Goal:
    """Edit a goal and recalculate status/notifications."""
    goal = get_goal(db, user.id, goal_id)
    previous_percentage = calculate_completion_percentage(
        goal.current_value, goal.target_value
    )
    previous_status = goal.status

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)

    db.flush()
    _refresh_goal_status(goal)
    notify_goal_change(db, goal, previous_percentage, previous_status)
    db.commit()
    db.refresh(goal)
    return goal


def update_goal_progress(
    db: Session, user: User, goal_id: int, payload: GoalProgressUpdate
) -> Goal:
    """Update the current progress value of a goal."""
    goal = get_goal(db, user.id, goal_id)
    previous_percentage = calculate_completion_percentage(
        goal.current_value, goal.target_value
    )
    previous_status = goal.status

    goal.current_value = payload.current_value
    db.flush()
    _refresh_goal_status(goal)
    notify_goal_change(db, goal, previous_percentage, previous_status)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, user: User, goal_id: int) -> None:
    """Delete an owned goal."""
    goal = get_goal(db, user.id, goal_id)
    db.delete(goal)
    db.commit()


def goal_summary(goals: list[Goal]) -> dict:
    """Return goal counts by status."""
    return {
        "total": len(goals),
        "active": sum(1 for goal in goals if goal.status == "active"),
        "completed": sum(1 for goal in goals if goal.status == "completed"),
        "overdue": sum(1 for goal in goals if goal.status == "overdue"),
    }
