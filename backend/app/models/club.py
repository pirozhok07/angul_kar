from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Float, String, Integer, Date, Numeric, Boolean, Column,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.tournament_models.models.base import TournamentBase
class Club(TournamentBase):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)


class Coach(TournamentBase):
    __tablename__ = "coaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    second_name: Mapped[str] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    club_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clubs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "last_name",
            "first_name",
            "second_name",
            "club_id",
            name="uq_coach_club"
        ),
    )
