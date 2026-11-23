from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Float, String, Integer, Date, Numeric, Boolean, Column,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.tournament_models.models.base import TournamentBase
class Athlete(TournamentBase):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    second_name: Mapped[str] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(7), nullable=False)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(5,2), nullable=True)
    weight_fact: Mapped[Decimal | None] = mapped_column(Numeric(5,2), nullable=True)
    rank_kyu: Mapped[str | None] = mapped_column(String(5), nullable=False)
    rank_sport: Mapped[str | None] = mapped_column(String(5), nullable=False)
    # club: Mapped[str] = mapped_column(String(150), nullable=False)
    # coach: Mapped[str] = mapped_column(String(150), nullable=False)
    # is_present: Mapped[bool] = mapped_column(Boolean, default=False)
    # is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    registration_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    club = relationship("Club")
    coach = relationship("Coach")

    club_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clubs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    coach_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("coaches.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )


class AthleteCategory(TournamentBase):
    __tablename__ = "athlete_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "athlete_id",
            "category_id",
            name="uq_athlete_category"
        ),
    )
