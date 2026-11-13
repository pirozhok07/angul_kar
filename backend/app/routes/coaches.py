from datetime import date
from decimal import Decimal
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func, inspect

from app.tournament_database import get_tournament_db
from app.tournament_models import Coach, Club
from app.models import Tournament
from app.database import get_db

router = APIRouter(
    prefix="/api/tournaments/{tournament_id}/coaches",
    tags=["Coachs"]
)

def serialize_coach(coach: Coach) -> dict[str, Any]:
    return {
        column.key: getattr(coach, column.key)
        for column in inspect(Coach).columns
    }

def validate_coach_data(data: dict[str, any], db: Session) -> dict[str, Any]:
    columns = {
        column.key
        for column in inspect(Coach).columns
    }
    protected = {"id"}
    allowed = columns - protected

    unknown = set(data.keys()) - allowed
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Неизвестное поле: {', '.join(sorted(unknown))}"
        )
    
    for field in ("first_name", "last_name"):
        value = str(data.get(field) or "").strip()

        if not value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Поле {field} обязательно"
            )
        
        data[field] = value

    if "club_id" in data and data["club_id"] is not None:
        try:
            club_id = int(data["club_id"])
        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Некорректный ID клуба: {e}"
            )
        club = db.get(Club, club_id)

        if not club:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клуб не найден"
            )
        
        data["club_id"] = club_id

    return data

def find_duplicate_coach(
    db: Session,
    first_name: str,
    second_name: str,
    last_name: str,
    club_id: int | None,
    exclude_id: int | None = None,
):
    query = db.query(Coach).filter(
        Coach.first_name == first_name, 
        Coach.second_name == second_name,
        Coach.last_name == last_name
    )

    if club_id is None:
        query = query.filter(Coach.club_id.is_(None))
    else:
        query = query.filter(Coach.club_id == club_id)

    if exclude_id is not None:
        query = query.filter(Coach.id != exclude_id)

    return query.first()

@router.get("/fields")
def get_coachs_fields(db: Session = Depends(get_tournament_db)):
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
        for column in inspect(Coach).columns
    ]

@router.get("/")
def get_coachs(db: Session = Depends(get_tournament_db)):
    coaches = db.query(Coach).order_by(Coach.id.desc()).all()
    return [serialize_coach(item) for item in coaches]

@router.get("/{coach_id}")
def get_coach(
    coach_id: int,
    db: Session = Depends(get_tournament_db)
):
    db_coach = db.get(Coach, coach_id)

    if db_coach is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found"
        )
    
    return serialize_coach(db_coach)

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_coach(
    data: dict[str, Any],
    db: Session = Depends(get_tournament_db)
):
    coach_data = validate_coach_data(data, db)

    duplicate = find_duplicate_coach(
        db=db,
        first_name=coach_data["first_name"],
        second_name=coach_data["second_name"],
        last_name=coach_data["last_name"],
        club_id=coach_data.get("club_id"),
    )

    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="Такой тренер уже зарегистрирован в этом клубе",
        )

    db_coach = Coach(**coach_data)

    db.add(db_coach)
    db.commit()
    db.refresh(db_coach)

    return serialize_coach(db_coach)

@router.put("/{coach_id}")
def update_coach(
    coach_id: int,
    data: dict[str, Any],
    db: Session = Depends(get_tournament_db)
):
    db_coach = db.get(Coach, coach_id)

    if db_coach is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found"
        )
    
    coach_data = validate_coach_data(data, db)

    if not (
        db_coach.first_name ==coach_data["first_name"]
        and db_coach.second_name ==coach_data["second_name"]
        and db_coach.last_name ==coach_data["last_name"]
    ):
        duplicate = find_duplicate_coach(
            db=db,
            first_name=coach_data["first_name"],
            second_name=coach_data["second_name"],
            last_name=coach_data["last_name"],
            club_id=coach_data.get("club_id"),
        )

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="Такой тренер уже зарегистрирован в этом клубе",
            )

    for key, value in coach_data.items():
        setattr(db_coach, key, value)

    db.commit()
    db.refresh(db_coach)

    return serialize_coach(db_coach)

@router.delete("/{coach_id}")
def delete_coach(
    coach_id: int,
    db: Session = Depends(get_tournament_db)
):
    db_coach = db.get(Coach, coach_id)
    
    if db_coach is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found"
        )

    db.delete(db_coach)
    db.commit()

@router.get("/{coach_id}")
def get_coach(
    coach_id: int,
    db: Session = Depends(get_tournament_db)
):
    db_coach = db.get(Coach, coach_id)

    if db_coach is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found"
        )
    
    return serialize_coach(db_coach)