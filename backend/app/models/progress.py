"""Daily progress ORM model.

Progress rows are a synchronized aggregation of the user's workouts for a
given day. Workout mutations recalculate the affected day so the stored
values never drift from the source workout records.
"""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Progress(Base):
    """Aggregated workout statistics for one user and one day."""

    __tablename__ = "progress"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_progress_user_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    total_workouts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_calories: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_duration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    user: Mapped["User"] = relationship(back_populates="progress_records")
