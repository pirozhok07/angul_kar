from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Float, String, Integer, Date, Numeric, Boolean, Column,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.tournament_models.models.base import TournamentBase
class KumiteTatami(TournamentBase):
    __tablename__ = "kumite_tatamis"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(50), nullable=False, unique=True)
    number: Mapped[int] = Column(Integer, nullable=False, unique=True)


class KataTatami(TournamentBase):
    __tablename__ = "kata_tatamis"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(50), nullable=False, unique=True)
    number: Mapped[int] = Column(Integer, nullable=False, unique=True)


class CategoryTatami(TournamentBase):
    __tablename__ = "category_tatamis"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    position: Mapped[int] = Column(Integer, nullable=False, default=0)

    category_id: Mapped[int] = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    kata_tatami_id: Mapped[int] = Column(
        Integer,
        ForeignKey("kata_tatamis.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    kumite_tatami_id: Mapped[int] = Column(
        Integer,
        ForeignKey("kumite_tatamis.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
