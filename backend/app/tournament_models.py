from datetime import date
from decimal import Decimal
from sqlalchemy import CheckConstraint, String, Integer, Date, Numeric, Boolean, Column, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class TournamentBase(DeclarativeBase):
    pass

class Athlete(TournamentBase):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    second_name: Mapped[str] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
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

    club_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("clubs.id", ondelete="SET NULL"), 
        nullable=False,
        index=True
    )

    coach_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("coaches.id", ondelete="SET NULL"), 
        nullable=False,
        index=True
    )

class Category(TournamentBase):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    discipline: Mapped[str] = mapped_column(String(100), nullable=False)
    gender: Mapped[str] = mapped_column(String(7), nullable=False)
    age_min: Mapped[int] = mapped_column(Integer, nullable=False)
    age_max: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_min: Mapped[Decimal | None] = mapped_column(Numeric(5,2), nullable=True)
    weight_max: Mapped[Decimal | None] = mapped_column(Numeric(5,2), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "discipline IN ('kata', 'kumite')",
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
        nullable=False,
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