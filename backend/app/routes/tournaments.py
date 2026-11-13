from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.database import get_db
from app.models import Tournament
from app.schemas import (
    TournamentCreate,
    TournamentResponse
)
from app.tournament_database import (
    get_tournament_db,
    get_database_name,
    provision_tournament_database
)
from app.tournament_models import Athlete

router = APIRouter(
    prefix="/api/tournaments",
    tags=["Tournaments"]
)

@router.get("/", response_model=list[TournamentResponse])
def get_tournaments(db: Session = Depends(get_db)):
    query = select(Tournament).order_by(Tournament.id.desc())
    return db.scalars(query).all()

@router.get("/{tournament_id}", response_model=TournamentResponse)
def get_tournament(
    tournament_id: int,
    db: Session = Depends(get_db)
):
    db_tournament = db.get(Tournament, tournament_id)

    if db_tournament is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found"
        )
    
    return db_tournament

@router.post("/", response_model=TournamentResponse, status_code=201)
def create_tournament(
    data: TournamentCreate,
    db: Session = Depends(get_db)
):
    db_tournament = Tournament(**data.model_dump(), database_status="provisioning")

    db.add(db_tournament)
    db.commit()
    db.refresh(db_tournament)

    database_name = get_database_name(db_tournament.id)

    db_tournament.database_name = database_name
    db.commit()

    try:
        provision_tournament_database(database_name)

        db_tournament.database_status = "ready"
        db.commit()
        db.refresh(db_tournament)

        return db_tournament
    
    except Exception as e:
        db.rollback()
        failed_tournament = db.get(
            Tournament,
            db_tournament.id
        )

        if failed_tournament:
            failed_tournament.database_name = database_name
            failed_tournament.database_status = "failed"

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tournament database: {e}"
        )

@router.put("/{tournament_id}", response_model=TournamentResponse)
def update_tournament(
    tournament_id: int,
    data: TournamentCreate,
    db: Session = Depends(get_db)
):
    db_tournament = db.get(Tournament, tournament_id)

    if db_tournament is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found"
        )
    
    for key, value in data.model_dump().items():
        setattr(db_tournament, key, value)

    db.commit()
    db.refresh(db_tournament)

    return db_tournament

@router.delete("/{tournament_id}", status_code=204)
def delete_tournament(
    tournament_id: int,
    db: Session = Depends(get_db)
):
    db_tournament = db.get(Tournament, tournament_id)

    # if db_tournament.database_name:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail="Tournament database deletion is not implement yet"
    #     )
    
    if db_tournament is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found"
        )

    db.delete(db_tournament)
    db.commit()

    
@router.get("/{tournament_id}/database-check")
def check_tournament_database(
    tournament_id: int,
    db: Session = Depends(get_tournament_db)
):
    athletes_count = db.scalar(
        select(func.count()).select_from(Athlete)
    )

    return {
        "tournament_id": tournament_id,
        "connection": "succesfull",
        "athletes_count": athletes_count
    }