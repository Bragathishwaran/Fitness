"""Fitness goal routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.goal import Goal
from app.models.user import User
from app.schemas.goal import (
    GoalCreate,
    GoalList,
    GoalOut,
    GoalProgressUpdate,
    GoalUpdate,
)
from app.services import goal_service
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/goals", tags=["Goals"])


@router.get("", response_model=GoalList, summary="List goals with status counts")
def list_goals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalList:
    goals = goal_service.list_goals(db, current_user.id)
    summary = goal_service.goal_summary(goals)
    return GoalList(items=goals, **summary)


@router.post(
    "",
    response_model=GoalOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a fitness goal",
)
def create_goal(
    payload: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Goal:
    return goal_service.create_goal(db, current_user, payload)


@router.get(
    "/{goal_id}",
    response_model=GoalOut,
    summary="Get one goal",
    responses={404: {"description": "Goal not found"}},
)
def get_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Goal:
    return goal_service.get_goal(db, current_user.id, goal_id)


@router.put(
    "/{goal_id}",
    response_model=GoalOut,
    summary="Update a goal",
    responses={404: {"description": "Goal not found"}},
)
def update_goal(
    goal_id: int,
    payload: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Goal:
    return goal_service.update_goal(db, current_user, goal_id, payload)


@router.patch(
    "/{goal_id}/progress",
    response_model=GoalOut,
    summary="Update current goal progress",
    responses={404: {"description": "Goal not found"}},
)
def update_goal_progress(
    goal_id: int,
    payload: GoalProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Goal:
    return goal_service.update_goal_progress(db, current_user, goal_id, payload)


@router.delete(
    "/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a goal",
    responses={404: {"description": "Goal not found"}},
)
def delete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    goal_service.delete_goal(db, current_user, goal_id)
