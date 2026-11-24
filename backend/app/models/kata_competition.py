from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Float, String, Integer, Date, Numeric, Boolean, Column,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.tournament_models.models.base import TournamentBase
class KataCompetition(TournamentBase):
    __tablename__ = "kata_competitions"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    category_id: Mapped[int] = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    status: Mapped[str] = Column(String(20), nullable=False, default="created")


class KataRound(TournamentBase):
    __tablename__ = "kata_rounds"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    competition_id: Mapped[int] = Column(
        Integer,
        ForeignKey("kata_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    number: Mapped[int] = Column(Integer, nullable=False)
    round_type: Mapped[str] = Column(String(20), nullable=False, default="regular")
    status: Mapped[str] = Column(String(20), nullable=False, default="pending")
    source_round_id: Mapped[int] = Column(
        Integer,
        ForeignKey("kata_rounds.id", ondelete="CASCADE"),
        nullable=True
    )

    advancement_limit: Mapped[int] = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "competition_id",
            "number",
            name="uq_kata_round_competition_number"
        ),
    )


class KataRoundParticipant(TournamentBase):
    __tablename__ = "kata_round_participants"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    round_id: Mapped[int] = Column(
        Integer,
        ForeignKey("kata_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    athlete_id: Mapped[int] = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    kata_group_id: Mapped[int] = Column(
        Integer,
        ForeignKey("kata_groups.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    position: Mapped[int] = Column(Integer, nullable=False)
    total_score: Mapped[float] = Column(Float, nullable=True)

    __table_args__ = (
        CheckConstraint(
            """
            (athlete_id IS NOT NULL AND kata_group_id IS NULL)
            OR
            (athlete_id IS NULL AND kata_group_id IS NOT NULL)
            """,
            name="ck_kata_round_participant_one_type"
        ),
        UniqueConstraint(
            "round_id",
            "athlete_id",
            name="uq_kata_round_athlete"
        ),
        UniqueConstraint(
            "round_id",
            "kata_group_id",
            name="uq_kata_round_group"
        ),
    )


class KataCompetitionResult(TournamentBase):
    __tablename__ = "kata_competition_results"

    id = Column(Integer, primary_key=True, index=True)

    competition_id = Column(
        Integer,
        ForeignKey("kata_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    athlete_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=True
    )

    kata_group_id = Column(
        Integer,
        ForeignKey("kata_groups.id", ondelete="CASCADE"),
        nullable=True
    )

    place = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint(
            """
            (athlete_id IS NOT NULL AND kata_group_id IS NULL)
            OR
            (athlete_id IS NULL AND kata_group_id IS NOT NULL)
            """,
            name="ck_kata_result_one_type"
        ),
        UniqueConstraint(
            "competition_id",
            "athlete_id",
            name="uq_kata_result_athlete"
        ),
        UniqueConstraint(
            "competition_id",
            "kata_group_id",
            name="uq_kata_result_group"
        ),
        UniqueConstraint(
            "competition_id",
            "place",
            name="uq_kata_result_place"
        ),
    )
