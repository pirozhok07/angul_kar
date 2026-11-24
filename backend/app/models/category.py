from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Float, String, Integer, Date, Numeric, Boolean, Column,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.tournament_models.models.base import TournamentBase
class Category(TournamentBase):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    discipline: Mapped[str] = mapped_column(String(100), nullable=False)
    gender: Mapped[str] = mapped_column(String(7), nullable=True)
    age_min: Mapped[int] = mapped_column(Integer, nullable=False)
    age_max: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_min: Mapped[Decimal | None] = mapped_column(Numeric(5,2), nullable=True)
    weight_max: Mapped[Decimal | None] = mapped_column(Numeric(5,2), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "discipline IN ('kata', 'kumite', 'kata-group')",
            name="check_category_discipline"
        ),
        CheckConstraint(
            "age_min < age_max",
            name="check_category_age"
        ),
        CheckConstraint(
            "discipline = 'kumite' OR "
            "(weight_min IS NULL AND weight_max IS NULL)",
            name="check_kata_without_weight"
        ),
        CheckConstraint(
            "weight_min IS NULL OR weight_max IS NULL "
            "OR weight_min < weight_max ",
            name="check_category_weight"
        ),
    )
