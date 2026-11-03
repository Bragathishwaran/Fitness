"""Analytics and dashboard aggregation."""

from collections import defaultdict
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.workout import Workout
from app.services.goal_service import list_goals
from app.services.progress_service import validate_range
from app.services.workout_service import get_recent_workouts
from app.utils.time import today_utc


def _aggregate_by_day(
    db: Session, user_id: int, start_date: date, end_date: date
) -> dict[date, dict]:
    """Group workouts by day for a date range."""
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

    return {
        row[0]: {
            "workouts": int(row[1]),
            "calories": int(row[2]),
            "duration": int(row[3]),
        }
        for row in rows
    }


def daily_activity(
    db: Session, user_id: int, start_date: date, end_date: date
) -> list[dict]:
    """Return one activity point per day, including empty days."""
    by_day = _aggregate_by_day(db, user_id, start_date, end_date)
    points: list[dict] = []
    current = start_date
    while current <= end_date:
        values = by_day.get(current, {"workouts": 0, "calories": 0, "duration": 0})
        points.append({"date": current, **values})
        current += timedelta(days=1)
    return points


def category_distribution(
    db: Session, user_id: int, start_date: date | None = None, end_date: date | None = None
) -> list[dict]:
    """Return workout counts and calorie totals per category."""
    filters = [Workout.user_id == user_id]
    if start_date:
        filters.append(Workout.workout_date >= start_date)
    if end_date:
        filters.append(Workout.workout_date <= end_date)

    rows = db.execute(
        select(
            Workout.category,
            func.count(Workout.id),
            func.coalesce(func.sum(Workout.calories_burned), 0),
        )
        .where(*filters)
        .group_by(Workout.category)
        .order_by(func.count(Workout.id).desc(), Workout.category.asc())
    ).all()

    total_workouts = sum(int(row[1]) for row in rows)
    return [
        {
            "category": row[0],
            "workouts": int(row[1]),
            "calories": int(row[2]),
            "percentage": round((int(row[1]) / total_workouts) * 100, 1)
            if total_workouts
            else 0.0,
        }
        for row in rows
    ]


def current_streak(db: Session, user_id: int) -> int:
    """Count consecutive days with at least one workout."""
    workout_dates = set(
        db.scalars(
            select(Workout.workout_date)
            .where(Workout.user_id == user_id)
            .distinct()
        )
    )
    if not workout_dates:
        return 0

    today = today_utc()
    cursor = today if today in workout_dates else today - timedelta(days=1)
    streak = 0
    while cursor in workout_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def get_dashboard(db: Session, user_id: int) -> dict:
    """Build the complete dashboard payload."""
    today = today_utc()
    week_start = today - timedelta(days=today.weekday())
    activity_start = today - timedelta(days=6)

    totals = db.execute(
        select(
            func.count(Workout.id),
            func.coalesce(func.sum(Workout.calories_burned), 0),
            func.coalesce(func.sum(Workout.duration), 0),
        ).where(Workout.user_id == user_id)
    ).one()

    week_totals = db.execute(
        select(
            func.count(Workout.id),
            func.coalesce(func.sum(Workout.calories_burned), 0),
        ).where(
            Workout.user_id == user_id,
            Workout.workout_date >= week_start,
            Workout.workout_date <= today,
        )
    ).one()

    goals = list_goals(db, user_id)
    active_goals = [goal for goal in goals if goal.status == "active"]

    return {
        "stats": {
            "total_workouts": int(totals[0]),
            "total_calories": int(totals[1]),
            "total_duration": int(totals[2]),
            "active_goals": len(active_goals),
            "completed_goals": sum(1 for goal in goals if goal.status == "completed"),
            "workouts_this_week": int(week_totals[0]),
            "calories_this_week": int(week_totals[1]),
            "current_streak": current_streak(db, user_id),
        },
        "weekly_activity": daily_activity(db, user_id, activity_start, today),
        "category_distribution": category_distribution(db, user_id),
        "recent_workouts": get_recent_workouts(db, user_id, limit=5),
        "goal_overview": active_goals[:4],
    }


def get_overview(
    db: Session, user_id: int, start_date: date, end_date: date
) -> dict:
    """Build the custom-range analytics payload."""
    validate_range(start_date, end_date)

    totals = db.execute(
        select(
            func.count(Workout.id),
            func.coalesce(func.sum(Workout.calories_burned), 0),
            func.coalesce(func.sum(Workout.duration), 0),
        ).where(
            Workout.user_id == user_id,
            Workout.workout_date >= start_date,
            Workout.workout_date <= end_date,
        )
    ).one()

    total_workouts = int(totals[0])
    total_calories = int(totals[1])
    total_duration = int(totals[2])
    activity = daily_activity(db, user_id, start_date, end_date)
    active_days = sum(1 for point in activity if point["workouts"] > 0)
    days = (end_date - start_date).days + 1
    weeks = max(days / 7, 1)
    distribution = category_distribution(db, user_id, start_date, end_date)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "totals": {
            "total_workouts": total_workouts,
            "total_calories": total_calories,
            "total_duration": total_duration,
            "average_duration": round(total_duration / total_workouts, 1)
            if total_workouts
            else 0.0,
            "average_calories": round(total_calories / total_workouts, 1)
            if total_workouts
            else 0.0,
            "active_days": active_days,
            "workouts_per_week": round(total_workouts / weeks, 1),
        },
        "daily_activity": activity,
        "category_distribution": distribution,
        "top_category": distribution[0]["category"] if distribution else None,
    }


def get_weekly_summary(
    db: Session, user_id: int, start_date: date, end_date: date
) -> list[dict]:
    """Group daily activity into Monday-starting weeks."""
    validate_range(start_date, end_date)
    activity = daily_activity(db, user_id, start_date, end_date)

    buckets: dict[date, dict] = defaultdict(
        lambda: {"workouts": 0, "calories": 0, "duration": 0}
    )
    for point in activity:
        week_start = point["date"] - timedelta(days=point["date"].weekday())
        buckets[week_start]["workouts"] += point["workouts"]
        buckets[week_start]["calories"] += point["calories"]
        buckets[week_start]["duration"] += point["duration"]

    result: list[dict] = []
    for week_start in sorted(buckets):
        week_end = week_start + timedelta(days=6)
        result.append(
            {
                "week_start": week_start,
                "week_end": week_end,
                "label": f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
                **buckets[week_start],
            }
        )
    return result


def _shift_month(value: date, delta: int) -> date:
    """Shift a first-of-month date by a number of months."""
    month_index = value.year * 12 + (value.month - 1) + delta
    year, month = divmod(month_index, 12)
    return date(year, month + 1, 1)


def get_monthly_summary(db: Session, user_id: int, months: int = 6) -> list[dict]:
    """Return the last N months of aggregated activity."""
    months = max(1, min(months, 24))
    today = today_utc()
    first_month = _shift_month(today.replace(day=1), -(months - 1))
    activity = daily_activity(db, user_id, first_month, today)

    buckets: dict[str, dict] = {}
    cursor = first_month
    while cursor <= today:
        key = cursor.strftime("%Y-%m")
        buckets[key] = {
            "month": key,
            "label": cursor.strftime("%b %Y"),
            "workouts": 0,
            "calories": 0,
            "duration": 0,
        }
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1, day=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1, day=1)

    for point in activity:
        key = point["date"].strftime("%Y-%m")
        if key in buckets:
            buckets[key]["workouts"] += point["workouts"]
            buckets[key]["calories"] += point["calories"]
            buckets[key]["duration"] += point["duration"]

    return list(buckets.values())


def get_category_breakdown(
    db: Session, user_id: int, start_date: date | None, end_date: date | None
) -> list[dict]:
    """Return category distribution, validating the optional range."""
    if start_date and end_date:
        validate_range(start_date, end_date)
    return category_distribution(db, user_id, start_date, end_date)


def get_frequency(db: Session, user_id: int, days: int = 30) -> dict:
    """Return simple workout frequency statistics."""
    days = max(1, min(days, 366))
    today = today_utc()
    start_date = today - timedelta(days=days - 1)
    activity = daily_activity(db, user_id, start_date, today)
    total = sum(point["workouts"] for point in activity)
    active_days = sum(1 for point in activity if point["workouts"] > 0)
    return {
        "days": days,
        "total_workouts": total,
        "active_days": active_days,
        "average_per_day": round(total / days, 2),
        "average_per_week": round(total / (days / 7), 2),
        "current_streak": current_streak(db, user_id),
    }
