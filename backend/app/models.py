from sqlalchemy import String, Integer, Date, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    database_name: Mapped[str | None] = mapped_column(String(63), unique=True, nullable=True)
    database_status: Mapped[str] = mapped_column(String(20), default="provisioning", nullable=False)