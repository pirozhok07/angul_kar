from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Float, String, Integer, Date, Numeric, Boolean, Column,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.tournament_models.models.base import TournamentBase
class KataGroup(TournamentBase):
    __tablename__ = "kata_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "name",
            "category_id",
            name="uq_kata_group_category"
        ),
    )


class KataGroupAthlete(TournamentBase):
    __tablename__ = "kata_group_athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    kata_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("kata_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    athlete_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "kata_group_id",
            "athlete_id",
            name="uq_kata_group_athlete"
        ),
    )
