from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Float, String, Integer, Date, Numeric, Boolean, Column,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.tournament_models.models.base import TournamentBase
class KataScore(TournamentBase):
    __tablename__ = "kata_scores"

    id = Column(Integer, primary_key=True, index=True)

    round_participant_id = Column(
        Integer,
        ForeignKey("kata_round_participants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    score1 = Column(Float, nullable=True)
    score2 = Column(Float, nullable=True)
    score3 = Column(Float, nullable=True)
    score4 = Column(Float, nullable=True)
    score5 = Column(Float, nullable=True)

    total_score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)
    min_score = Column(Float, nullable=True)

    is_confirmed = Column(Boolean, nullable=False, default=False)
