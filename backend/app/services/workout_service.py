"""Workout CRUD and daily progress synchronization."""

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.progress import Progress
from app.models.user import User
from app.models.workout import Workout
from app.schemas.workout import WorkoutCreate, WorkoutUpdate


def sync_day(db: Session, user_id: int, workout_date: date) -> None:
    """Recalculate and upsert the progress row for one user/day.

    The workout records are the source of truth. This keeps the denormalized
    progress table consistent after every create, update and delete.
    """
    totals = db.execute(
        select(
            func.count(Workout.id),
            func.coalesce(func.sum(Workout.calories_burned), 0),
            func.coalesce(func.sum(Workout.duration), 0),
        ).where(
            Workout.user_id == user_id,
            Workout.workout_date == workout_date,
        )
    ).one()

    total_workouts = int(totals[0])
    existing = db.scalar(
        select(Progress).where(
            Progress.user_id == user_id,
            Progress.date == workout_date,
        )
    )

    if total_workouts == 0:
        if existing:
            db.delete(existing)
        return

    if existing:
        existing.total_workouts = total_workouts
        existing.total_calories = int(totals[1])
        existing.total_duration = int(totals[2])
    else:
        db.add(
            Progress(
                user_id=user_id,
                date=workout_date,
                total_workouts=total_workouts,
                total_calories=int(totals[1]),
                total_duration=int(totals[2]),
            )
        )


def list_workouts(
    db: Session,
    user_id: int,
    *,
    search: str | None = None,
    category: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Workout], int]:
    """Return a filtered, paginated list of the user's workouts."""
    filters = [Workout.user_id == user_id]
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Workout.workout_name.ilike(pattern),
                Workout.category.ilike(pattern),
            )
        )
    if category:
        filters.append(Workout.category == category)
    if start_date:
        filters.append(Workout.workout_date >= start_date)
    if end_date:
        filters.append(Workout.workout_date <= end_date)

    total = db.scalar(select(func.count(Workout.id)).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Workout)
            .where(*filters)
            .order_by(Workout.workout_date.desc(), Workout.id.desc())
            .offset(skip)
            .limit(limit)
        )
    )
    return items, int(total)


def get_workout(db: Session, user_id: int, workout_id: int) -> Workout:
    """Fetch a workout and enforce ownership."""
    workout = db.get(Workout, workout_id)
    if not workout or workout.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found",
        )
    return workout


def create_workout(db: Session, user: User, payload: WorkoutCreate) -> Workout:
    """Create a workout and synchronize its daily progress."""
    workout = Workout(user_id=user.id, **payload.model_dump())
    db.add(workout)
    db.flush()
    sync_day(db, user.id, workout.workout_date)
    db.commit()
    db.refresh(workout)
    return workout


def update_workout(
    db: Session, user: User, workout_id: int, payload: WorkoutUpdate
) -> Workout:
    """Update an owned workout and resync both affected days."""
    workout = get_workout(db, user.id, workout_id)
    previous_date = workout.workout_date

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(workout, field, value)

    db.flush()
    sync_day(db, user.id, previous_date)
    if workout.workout_date != previous_date:
        sync_day(db, user.id, workout.workout_date)
    db.commit()
    db.refresh(workout)
    return workout


def delete_workout(db: Session, user: User, workout_id: int) -> None:
    """Delete an owned workout and resync its day."""
    workout = get_workout(db, user.id, workout_id)
    workout_date = workout.workout_date
    db.delete(workout)
    db.flush()
    sync_day(db, user.id, workout_date)
    db.commit()


def get_recent_workouts(db: Session, user_id: int, limit: int = 5) -> list[Workout]:
    """Return the most recent workouts for the dashboard."""
    return list(
        db.scalars(
            select(Workout)
            .where(Workout.user_id == user_id)
            .order_by(Workout.workout_date.desc(), Workout.id.desc())
            .limit(limit)
        )
    )
