
import re

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.database.master import DATABASE_URL
from app.database.manager import tournament_db_manager
from app.tournament_models import TournamentBase


# ============================================================
# Admin Engine
# ============================================================

admin_url = make_url(DATABASE_URL).set(
    database="postgres"
)

admin_engine = create_engine(
    admin_url,
    isolation_level="AUTOCOMMIT",
    pool_pre_ping=True,
)


# ============================================================
# Database Naming
# ============================================================

def get_database_name(tournament_id: int) -> str:
    return f"karate_event_{tournament_id}"


def validate_database_name(database_name: str) -> None:
    if not re.fullmatch(r"karate_event_[0-9]+", database_name):
        raise ValueError("Invalid tournament database name")


# ============================================================
# Provision Tournament Database
# ============================================================

def provision_tournament_database(database_name: str) -> None:

    validate_database_name(database_name)

    # Проверяем существование базы
    with admin_engine.connect() as conn:

        exists = conn.execute(
            text("""
                SELECT 1
                FROM pg_database
                WHERE datname = :database_name
            """),
            {"database_name": database_name},
        ).scalar()

        # Создаём базу, если её ещё нет
        if not exists:
            quoted_name = (
                admin_engine.dialect
                .identifier_preparer
                .quote_identifier(database_name)
            )

            conn.exec_driver_sql(
                f"CREATE DATABASE {quoted_name}"
            )

    # Создаём таблицы турнира
    engine = tournament_db_manager.get_engine(database_name)

    TournamentBase.metadata.create_all(bind=engine)


# ============================================================
# Delete Tournament Database
# ============================================================

def drop_tournament_database(database_name: str) -> None:

    validate_database_name(database_name)

    # Закрываем Engine и пул соединений
    tournament_db_manager.dispose(database_name)

    quoted_name = (
        admin_engine.dialect
        .identifier_preparer
        .quote_identifier(database_name)
    )

    # Завершаем подключения и удаляем базу
    with admin_engine.connect() as conn:

        conn.execute(
            text("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = :database_name
                  AND pid <> pg_backend_pid()
            """),
            {"database_name": database_name},
        )

        conn.exec_driver_sql(
            f"DROP DATABASE IF EXISTS {quoted_name}"
        )
