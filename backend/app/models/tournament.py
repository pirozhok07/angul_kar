from datetime import date

from sqlalchemy import (
    String,
    Integer,
    Date,
    Text,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.master import Base


class Tournament(Base):
    """
    Модель турнира в главной базе данных.

    Хранит информацию о турнире и имя отдельной базы данных,
    в которой находятся участники, категории, результаты и другие данные.
    """

    __tablename__ = "tournaments"

    __table_args__ = (
        CheckConstraint(
            "end_date >= start_date",
            name="check_tournament_dates",
        ),
    )

    # Основные данные турнира
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    location: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Настройки отдельной базы данных турнира
    database_name: Mapped[str | None] = mapped_column(
        String(63),
        unique=True,
        nullable=True,
    )

    database_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="provisioning",
    )