"""ORM models package.

Importing the models here ensures they are all registered on ``Base.metadata``
before table creation and Alembic autogeneration.
"""

from app.models.goal import GOAL_TYPES, Goal
from app.models.notification import Notification
from app.models.progress import Progress
from app.models.user import User
from app.models.workout import WORKOUT_CATEGORIES, Workout

__all__ = [
    "User",
    "Workout",
    "Progress",
    "Goal",
    "Notification",
    "WORKOUT_CATEGORIES",
    "GOAL_TYPES",
]
