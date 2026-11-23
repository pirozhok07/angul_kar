from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.tournament import get_tournament_db
from app.tournament_models import Club

router = APIRouter(
    prefix="/api/tournaments/{tournament_id}/clubs",
    tags=["Clubs"],
)


def serialize_club(club: Club) -> dict[str, Any]:
    """Преобразует ORM-объект клуба в словарь колонок."""
    return {
        column.key: getattr(club, column.key)
        for column in inspect(Club).columns
    }


def validate_club_data(
    data: dict[str, Any],
    *,
    creating: bool = False,
) -> dict[str, Any]:
    """Проверяет входные поля по фактической структуре модели Club."""
    data = dict(data)
    columns = {column.key: column for column in inspect(Club).columns}

    protected = {"id"}
    allowed = set(columns) - protected
    unknown = set(data) - allowed

    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Неизвестные поля: {', '.join(sorted(unknown))}",
        )

    if creating:
        required_fields = {
            key
            for key, column in columns.items()
            if key not in protected
            and not column.nullable
            and column.default is None
            and column.server_default is None
        }
        missing = required_fields - set(data)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Не заполнены обязательные поля: {', '.join(sorted(missing))}",
            )

    for key, value in data.items():
        column = columns[key]
        if value is None and not column.nullable and column.default is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Поле '{key}' не может быть null",
            )

    if "name" in data:
        name = str(data["name"] or "").strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Название клуба не может быть пустым",
            )
        data["name"] = name

    return data


@router.get("/fields")
def get_club_fields(
    tournament_id: int,
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
        for column in inspect(Club).columns
    ]


@router.get("/")
def get_clubs(
    tournament_id: int,
    db: Session = Depends(get_tournament_db),
):
    clubs = db.query(Club).order_by(Club.id.desc()).all()
    return [serialize_club(club) for club in clubs]


@router.get("/{club_id}")
def get_club(
    tournament_id: int,
    club_id: int,
    db: Session = Depends(get_tournament_db),
):
    club = db.get(Club, club_id)
    if club is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клуб не найден",
        )
    return serialize_club(club)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_club(
    tournament_id: int,
    data: dict[str, Any] = Body(...),
    db: Session = Depends(get_tournament_db),
):
    club_data = validate_club_data(data, creating=True)
    club = Club(**club_data)

    try:
        db.add(club)
        db.commit()
        db.refresh(club)
        return serialize_club(club)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Не удалось создать клуб: нарушено ограничение базы данных (например, уникальность или внешний ключ)",
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка базы данных при создании клуба",
        )


@router.put("/{club_id}")
def update_club(
    tournament_id: int,
    club_id: int,
    data: dict[str, Any] = Body(...),
    db: Session = Depends(get_tournament_db),
):
    club = db.get(Club, club_id)
    if club is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клуб не найден",
        )

    club_data = validate_club_data(data)
    if not club_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Не переданы поля для обновления",
        )

    try:
        for key, value in club_data.items():
            setattr(club, key, value)
        db.commit()
        db.refresh(club)
        return serialize_club(club)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Не удалось обновить клуб: нарушено ограничение базы данных (например, уникальность или внешний ключ)",
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка базы данных при обновлении клуба",
        )


@router.delete("/{club_id}")
def delete_club(
    tournament_id: int,
    club_id: int,
    db: Session = Depends(get_tournament_db),
):
    club = db.get(Club, club_id)
    if club is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клуб не найден",
        )

    try:
        db.delete(club)
        db.commit()
        return {
            "message": "Клуб удалён",
            "club_id": club_id,
        }
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя удалить клуб: с ним связаны другие записи",
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка базы данных при удалении клуба",
        )
