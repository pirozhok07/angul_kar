from datetime import date
from decimal import Decimal
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func, inspect

from app.tournament_database import get_tournament_db
from app.tournament_models import Club
from app.models import Tournament
from app.database import get_db

router = APIRouter(
    prefix="/api/tournaments/{tournament_id}/clubs",
    tags=["Clubs"]
)

def serialize_club(club: Club) -> dict[str, Any]:
    return {
        column.key: getattr(club, column.key)
        for column in inspect(Club).columns
    }

def validate_club_data(data: dict[str, any]) -> dict[str, Any]:
    columns = {
        column.key
        for column in inspect(Club).columns
    }
    protected = {"id"}
    allowed = columns - protected

    unknown = set(data.keys()) - allowed
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Неизвестное поле: {', '.join(sorted(unknown))}"
        )
    
    if "name" in data:
        name = str(data["name"] or "").strip()

        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Название клуба не может быть пустым"
            )
        
        data["name"] = name

    return data

@router.get("/fields")
def get_clubs_fields(db: Session = Depends(get_tournament_db)):
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
        for column in inspect(Club).columns
    ]

@router.get("/")
def get_clubs(db: Session = Depends(get_tournament_db)):
    clubs = db.query(Club).order_by(Club.id.desc()).all()
    return [serialize_club(item) for item in clubs]

@router.get("/{club_id}")
def get_club(
    club_id: int,
    db: Session = Depends(get_tournament_db)
):
    db_club = db.get(Club, club_id)

    if db_club is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Club not found"
        )
    
    return serialize_club(db_club)

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_club(
    data: dict[str, Any],
    db: Session = Depends(get_tournament_db)
):
    db_club = Club(**validate_club_data(data))

    db.add(db_club)
    try:
        db.commit()
        db.refresh(db_club)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Клуб с таким названием уже существует"
        )

    return serialize_club(db_club)

@router.put("/{club_id}")
def update_club(
    club_id: int,
    data: dict[str, Any],
    db: Session = Depends(get_tournament_db)
):
    db_club = db.get(Club, club_id)

    if db_club is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Club not found"
        )
    
    club_data = validate_club_data(data)
    for key, value in club_data.items():
        setattr(db_club, key, value)

    try:
        db.commit()
        db.refresh(db_club)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Клуб с таким названием уже существует"
        )

    return serialize_club(db_club)

@router.delete("/{club_id}")
def delete_club(
    club_id: int,
    db: Session = Depends(get_tournament_db)
):
    db_club = db.get(Club, club_id)
    
    if db_club is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Club not found"
        )

    db.delete(db_club)
    db.commit()

@router.get("/{club_id}")
def get_club(
    club_id: int,
    db: Session = Depends(get_tournament_db)
):
    db_club = db.get(Club, club_id)

    if db_club is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Club not found"
        )
    
    return serialize_club(db_club)