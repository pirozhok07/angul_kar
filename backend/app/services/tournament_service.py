# app/services/tournament_service.py

from sqlalchemy.orm import Session

from app.models import Tournament
from app.database.provisioner import (
    get_database_name,
    provision_tournament_database,
)


# ============================================================
# Create Tournament
# ============================================================

def create_tournament(
    master_db: Session,
    tournament_data,
) -> Tournament:

    # --------------------------------------------------------
    # Create tournament record
    # --------------------------------------------------------

    tournament = Tournament(
        **tournament_data.model_dump(),
    )

    master_db.add(tournament)
    master_db.flush()

    # --------------------------------------------------------
    # Assign database name
    # --------------------------------------------------------

    tournament.database_name = get_database_name(
        tournament.id
    )

    tournament.database_status = "provisioning"

    master_db.commit()
    master_db.refresh(tournament)

    # --------------------------------------------------------
    # Provision database
    # --------------------------------------------------------

    try:

        provision_tournament_database(
            tournament.database_name
        )

        # ----------------------------------------------------
        # Mark as ready
        # ----------------------------------------------------

        tournament.database_status = "ready"

        master_db.commit()
        master_db.refresh(tournament)

    except Exception:

        master_db.rollback()

        # ----------------------------------------------------
        # Mark provisioning failed
        # ----------------------------------------------------

        failed_tournament = master_db.get(
            Tournament,
            tournament.id,
        )

        if failed_tournament is not None:

            failed_tournament.database_status = "failed"

            master_db.commit()

        raise

    return tournament