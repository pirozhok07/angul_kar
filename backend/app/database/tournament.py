# app/database/tournament.py

from collections.abc import Generator

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.master import get_db
from app.database.manager import tournament_db_manager
from app.models import Tournament


# ============================================================
# Tournament Database Dependency
# ============================================================

def get_tournament_db(
    tournament_id: int,
    master_db: Session = Depends(get_db),
) -> Generator[Session, None, None]:

    # --------------------------------------------------------
    # Get tournament
    # --------------------------------------------------------

    tournament = master_db.get(
        Tournament,
        tournament_id,
    )

    if tournament is None:
        raise HTTPException(
            status_code=404,
            detail="Tournament not found",
        )

    # --------------------------------------------------------
    # Validate database status
    # --------------------------------------------------------

    if (
        tournament.database_status != "ready"
        or not tournament.database_name
    ):
        raise HTTPException(
            status_code=409,
            detail="Tournament database is not ready",
        )

    # --------------------------------------------------------
    # Create session
    # --------------------------------------------------------

    db = tournament_db_manager.create_session(
        tournament.database_name
    )

    # --------------------------------------------------------
    # Yield session
    # --------------------------------------------------------

    try:
        yield db

    finally:
        db.close()