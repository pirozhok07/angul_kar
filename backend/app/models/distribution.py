from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Float, String, Integer, Date, Numeric, Boolean, Column,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.tournament_models.models.base import TournamentBase
class CategoryDistribution(TournamentBase):
    __tablename__ = "category_distributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    draw_order: Mapped[int] = mapped_column(Integer, nullable=True)

    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    athlete_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    kata_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("kata_groups.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "athlete_id",
            name="uq_category_distributions_athlete"
        ),
        UniqueConstraint(
            "category_id",
            "kata_group_id",
            name="uq_category_distributions_kata_group"
        ),
        CheckConstraint(
            """
            (athlete_id IS NOT NULL AND kata_group_id IS NULL)
            OR
            (athlete_id IS NULL AND kata_group_id IS NOT NULL)
            """,
            name="ck_category_distribution_one_participant"
        )
    )


class Undistribution(TournamentBase):
    __tablename__ = "undistributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    athlete_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
