"""Daily progress aggregation and history."""

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.workout import Workout
from app.services.workout_service import sync_day

MAX_RANGE_DAYS = 366


def validate_range(start_date: date, end_date: date) -> None:
    """Validate a date range used by progress and analytics endpoints."""
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be on or before end_date",
        )
    if (end_date - start_date).days > MAX_RANGE_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Date range cannot exceed {MAX_RANGE_DAYS} days",
        )


def get_daily_detail(db: Session, user_id: int, target_date: date) -> dict:
    """Return live statistics and workouts for a single day."""
    workouts = list(
        db.scalars(
            select(Workout)
            .where(
                Workout.user_id == user_id,
                Workout.workout_date == target_date,
            )
            .order_by(Workout.id.desc())
        )
    )
    total_calories = sum(workout.calories_burned for workout in workouts)
    total_duration = sum(workout.duration for workout in workouts)

    # Keep the denormalized table aligned with the live aggregation.
    sync_day(db, user_id, target_date)
    db.commit()

    return {
        "date": target_date,
        "total_workouts": len(workouts),
        "total_calories": total_calories,
        "total_duration": total_duration,
        "workouts": workouts,
    }


def get_summary(db: Session, user_id: int, start_date: date, end_date: date) -> dict:
    """Aggregate workout history into per-day rows for a date range."""
    validate_range(start_date, end_date)

    rows = db.execute(
        select(
            Workout.workout_date,
            func.count(Workout.id),
            func.coalesce(func.sum(Workout.calories_burned), 0),
            func.coalesce(func.sum(Workout.duration), 0),
        )
        .where(
            Workout.user_id == user_id,
            Workout.workout_date >= start_date,
            Workout.workout_date <= end_date,
        )
        .group_by(Workout.workout_date)
        .order_by(Workout.workout_date)
    ).all()

    by_day = {
        row[0]: {
            "date": row[0],
            "total_workouts": int(row[1]),
            "total_calories": int(row[2]),
            "total_duration": int(row[3]),
        }
        for row in rows
    }

    days: list[dict] = []
    current = start_date
    while current <= end_date:
        days.append(
            by_day.get(
                current,
                {
                    "date": current,
                    "total_workouts": 0,
                    "total_calories": 0,
                    "total_duration": 0,
                },
            )
        )
        current += timedelta(days=1)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_workouts": sum(day["total_workouts"] for day in days),
        "total_calories": sum(day["total_calories"] for day in days),
        "total_duration": sum(day["total_duration"] for day in days),
        "days": days,
    }
