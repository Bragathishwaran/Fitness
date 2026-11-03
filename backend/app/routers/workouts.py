"""Workout CRUD routes."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.workout import Workout
from app.schemas.workout import WorkoutCreate, WorkoutList, WorkoutOut, WorkoutUpdate
from app.services import workout_service
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/workouts", tags=["Workouts"])

CategoryFilter = Literal["Cardio", "Strength", "Yoga"]


@router.post(
    "",
    response_model=WorkoutOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a workout",
)
def create_workout(
    payload: WorkoutCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workout:
    return workout_service.create_workout(db, current_user, payload)


@router.get(
    "",
    response_model=WorkoutList,
    summary="List the current user's workouts",
    description="Supports search, category and date filters with pagination.",
)
def list_workouts(
    search: str | None = Query(default=None, max_length=120),
    category: CategoryFilter | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkoutList:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be on or before end_date",
        )
    items, total = workout_service.list_workouts(
        db,
        current_user.id,
        search=search,
        category=category,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return WorkoutList(items=items, total=total, skip=skip, limit=limit)


@router.get(
    "/{workout_id}",
    response_model=WorkoutOut,
    summary="Get one workout",
    responses={404: {"description": "Workout not found"}},
)
def get_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workout:
    return workout_service.get_workout(db, current_user.id, workout_id)


@router.put(
    "/{workout_id}",
    response_model=WorkoutOut,
    summary="Update a workout",
    responses={404: {"description": "Workout not found"}},
)
def update_workout(
    workout_id: int,
    payload: WorkoutUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workout:
    return workout_service.update_workout(db, current_user, workout_id, payload)


@router.delete(
    "/{workout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workout",
    responses={404: {"description": "Workout not found"}},
)
def delete_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    workout_service.delete_workout(db, current_user, workout_id)
