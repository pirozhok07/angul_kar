from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Float, String, Integer, Date, Numeric, Boolean, Column,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.tournament_models.models.base import TournamentBase
class BronzeMatchResult(TournamentBase):
    __tablename__ = "bronze_match_results"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    category_id: Mapped[int] = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    athlete1_id: Mapped[int] = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="SET NULL"),
        nullable=True
    )

    athlete2_id: Mapped[int] = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="SET NULL"),
        nullable=True
    )

    winner_athlete_id: Mapped[int] = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="SET NULL"),
        nullable=True
    )

    athlete1 = relationship("Athlete", foreign_keys=[athlete1_id])
    athlete2 = relationship("Athlete", foreign_keys=[athlete2_id])

    status: Mapped[str] = Column(String(20), nullable=False, default="pending")


class KumiteResult(TournamentBase):
    __tablename__ = "kumite_results"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    category_id: Mapped[int] = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    athlete_id: Mapped[int] = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    place: Mapped[int] = Column(Integer, nullable=False)

    athlete = relationship("Athlete")
    category = relationship("Category")

    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "athlete_id",
            name="uq_kumite_result_athlete"
        ),
        UniqueConstraint(
            "category_id",
            "place",
            name="uq_kumite_result_place"
        ),
    )
