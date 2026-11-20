from datetime import date, datetime, timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, inspect

from app.tournament_database import get_tournament_db
from app.tournament_models import Athlete
from app.models import Tournament
from app.database import get_db

router = APIRouter(
    prefix="/api/tournaments/{tournament_id}/athletes",
    tags=["Athletes"]
)

def serialize_athlete(athlete: Athlete) -> dict[str, Any]:
    return {
        column.key: getattr(athlete, column.key)
        for column in inspect(Athlete).columns
    }

def validate_athlete_data(data: dict[str, any]) -> dict[str, Any]:
    columns = {
        column.key
        for column in inspect(Athlete).columns
    }
    protected = {"id"}
    allowed = columns - protected

    unknown = set(data.keys()) - allowed
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Неизвестное поле: {', '.join(sorted(unknown))}"
        )
    return allowed

def get_tournament_date(main_db: Session, tournament_id: int) -> date:
    tournament = main_db.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found"
        )
    return tournament.start_date

def calculate_age(birth_date: date, tournament_date: date) -> int:
    control_date = tournament_date - timedelta(days=1)
    birth_date=datetime.strptime(birth_date, '%Y-%m-%d').date()
    return control_date.year-birth_date.year - (
        (control_date.month,control_date.day) < (birth_date.month, birth_date.day)
    )
    

@router.get("/fields")
def get_athlete_fields(db: Session = Depends(get_tournament_db)):
    return [
        {
            "name": column.key,
            "type": str(column.type),
            "nullable": column.nullable,
            "required": (
                not column.nullable
                and column.default is None
                and column.server_default is None
                and column.key != "id"
            ),
        }
        for column in inspect(Athlete).columns
    ]

@router.get("/")
def get_athletes(db: Session = Depends(get_tournament_db)):
    athletes = db.query(Athlete).order_by(Athlete.id.desc()).all()
    return [serialize_athlete(item) for item in athletes]

@router.get("/{athlete_id}")
def get_athlete(
    athlete_id: int,
    db: Session = Depends(get_tournament_db)
):
    db_athlete = db.get(Athlete, athlete_id)

    if db_athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found"
        )
    
    return serialize_athlete(db_athlete)

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_athlete(
    data: dict[str, Any],
    tournament_id: int,
    db: Session = Depends(get_tournament_db)
):
    db_athlete = Athlete(
        **validate_athlete_data(data),
        age = calculate_age(data['birth_date'], get_tournament_date(tournament_id)),
        registration_status="pending"
    )

    db.add(db_athlete)
    db.commit()
    db.refresh(db_athlete)

    return serialize_athlete(db_athlete)

@router.put("/{athlete_id}")
def update_athlete(
    athlete_id: int,
    tournament_id: int,
    data: dict[str, Any],
    db: Session = Depends(get_tournament_db),
    main_db: Session = Depends(get_db)
):
    db_athlete = db.get(Athlete, athlete_id)

    if db_athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found"
        )
    
    athlete_data = validate_athlete_data(data)
    if data.get('birth_date') is not None:
        data['age'] = calculate_age(data['birth_date'], get_tournament_date(main_db,tournament_id))
    for key in athlete_data:
        setattr(db_athlete, key, data[key])

    db.commit()
    db.refresh(db_athlete)

    return serialize_athlete(db_athlete)

@router.delete("/{athlete_id}")
def delete_athlete(
    athlete_id: int,
    db: Session = Depends(get_tournament_db)
):
    db_athlete = db.get(Athlete, athlete_id)
    
    if db_athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found"
        )

    db.delete(db_athlete)
    db.commit()