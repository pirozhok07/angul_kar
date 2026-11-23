
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.database.master import get_db
from app.database.tournament import get_tournament_db

from app.models import Tournament
from app.tournament_models import Athlete


router = APIRouter(
    prefix="/api/tournaments/{tournament_id}/athletes",
    tags=["Athletes"],
)


# ============================================================
# Serialization
# ============================================================

def serialize_athlete(athlete: Athlete) -> dict[str, Any]:
    return {
        column.key: getattr(athlete, column.key)
        for column in inspect(Athlete).columns
    }


# ============================================================
# Validation
# ============================================================

def validate_athlete_data(data: dict[str, Any]) -> dict[str, Any]:

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
            detail=f"Неизвестные поля: {', '.join(sorted(unknown))}",
        )

    return {
        key: value
        for key, value in data.items()
        if key in allowed
    }


# ============================================================
# Tournament Date
# ============================================================

def get_tournament_date(
    main_db: Session,
    tournament_id: int,
) -> date:

    tournament = main_db.get(Tournament, tournament_id)

    if tournament is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found",
        )

    return tournament.start_date


# ============================================================
# Age Calculation
# ============================================================

def calculate_age(
    birth_date: date | str,
    tournament_date: date,
) -> int:

    if isinstance(birth_date, str):
        try:
            birth_date = date.fromisoformat(birth_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid birth_date format. Use YYYY-MM-DD",
            )

    control_date = tournament_date - timedelta(days=1)

    if birth_date > control_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Birth date cannot be in the future",
        )

    return (
        control_date.year - birth_date.year
        - (
            (control_date.month, control_date.day)
            < (birth_date.month, birth_date.day)
        )
    )


# ============================================================
# GET: Athlete Fields
# ============================================================

@router.get("/fields")
def get_athlete_fields(
    db: Session = Depends(get_tournament_db),
):
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


# ============================================================
# GET: All Athletes
# ============================================================

@router.get("/")
def get_athletes(
    db: Session = Depends(get_tournament_db),
):
    athletes = (
        db.query(Athlete)
        .order_by(Athlete.id.desc())
        .all()
    )

    return [
        serialize_athlete(athlete)
        for athlete in athletes
    ]


# ============================================================
# GET: Athlete By ID
# ============================================================

@router.get("/{athlete_id}")
def get_athlete(
    athlete_id: int,
    db: Session = Depends(get_tournament_db),
):
    athlete = db.get(Athlete, athlete_id)

    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    return serialize_athlete(athlete)


# ============================================================
# POST: Create Athlete
# ============================================================

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
)
def create_athlete(
    tournament_id: int,
    data: dict[str, Any],
    db: Session = Depends(get_tournament_db),
    main_db: Session = Depends(get_db),
):
    athlete_data = validate_athlete_data(data)

    birth_date = athlete_data.get("birth_date")

    if birth_date is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="birth_date is required",
        )

    tournament_date = get_tournament_date(
        main_db,
        tournament_id,
    )

    athlete_data["age"] = calculate_age(
        birth_date,
        tournament_date,
    )

    athlete_data["registration_status"] = "pending"

    athlete = Athlete(**athlete_data)

    try:
        db.add(athlete)
        db.commit()
        db.refresh(athlete)

        return serialize_athlete(athlete)

    except Exception:
        db.rollback()
        raise


# ============================================================
# PUT: Update Athlete
# ============================================================

@router.put("/{athlete_id}")
def update_athlete(
    athlete_id: int,
    tournament_id: int,
    data: dict[str, Any],
    db: Session = Depends(get_tournament_db),
    main_db: Session = Depends(get_db),
):
    athlete = db.get(Athlete, athlete_id)

    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    athlete_data = validate_athlete_data(data)

    if "birth_date" in athlete_data:
        tournament_date = get_tournament_date(
            main_db,
            tournament_id,
        )

        athlete_data["age"] = calculate_age(
            athlete_data["birth_date"],
            tournament_date,
        )

    try:
        for key, value in athlete_data.items():
            setattr(athlete, key, value)

        db.commit()
        db.refresh(athlete)

        return serialize_athlete(athlete)

    except Exception:
        db.rollback()
        raise


# ============================================================
# DELETE: Athlete
# ============================================================

@router.delete(
    "/{athlete_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_athlete(
    athlete_id: int,
    db: Session = Depends(get_tournament_db),
):
    athlete = db.get(Athlete, athlete_id)

    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    db.delete(athlete)
    db.commit()

    return None
