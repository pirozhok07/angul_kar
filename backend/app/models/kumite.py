from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Float, String, Integer, Date, Numeric, Boolean, Column,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.tournament_models.models.base import TournamentBase
class KumiteDrawEntry(TournamentBase):
    __tablename__ = "kumite_draw_entries"

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

    draw_position: Mapped[int] = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "athlete_id",
            name="uq_kumite_draw_category_athlete"
        ),
        UniqueConstraint(
            "category_id",
            "draw_position",
            name="uq_kumite_draw_category_position"
        ),
    )


class KumiteDrawMatch(TournamentBase):
    __tablename__ = "kumite_draw_matches"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    round_number: Mapped[int] = Column(Integer, nullable=False)
    match_number: Mapped[int] = Column(Integer, nullable=False)

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
    athlete2= relationship("Athlete", foreign_keys=[athlete2_id])

    match_type: Mapped[str] = Column(String(20), nullable=False, default="regular")
    status: Mapped[str] = Column(String(20), nullable=False, default="pending")

    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "round_number",
            "match_number",
            name="uq_kumite_match_round"
        ),
    )
