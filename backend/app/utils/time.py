"""Shared time helpers.

The application stores naive UTC datetimes so that SQLite and PostgreSQL
behave consistently. Dates used for workouts/progress are calendar dates
chosen by the user.
"""

from datetime import date, datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC time as a naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def today_utc() -> date:
    """Return today's date in UTC."""
    return datetime.now(timezone.utc).date()
