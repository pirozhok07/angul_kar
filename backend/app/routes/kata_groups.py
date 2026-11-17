from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Body, status
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.tournament_database import get_tournament_db
from app.tournament_models import (
    KataGroup,
    KataGroupAthlete,
    Category,
    Athlete,
)

router = APIRouter(
    prefix="/api/tournaments/{tournament_id}/kata-groups",
    tags=["Kata Groups"],
)

def serialize_data(model) -> dict[str, Any]:
    return {
        column.key: getattr(model, column.key)
        for column in inspect(model).mapper.columns
    }

def get_athlete_display_name(athlete):
    parts = [
        getattr(athlete, "last_name", None),
        getattr(athlete, "first_name", None),
        getattr(athlete, "second_name", None),
    ]

    return " ".join(str(part).strip() for part in parts if part)


def get_group_data(db: Session, group: KataGroup):
    members = (
        db.query(Athlete)
        .join(
            KataGroupAthlete,
            KataGroupAthlete.athlete_id == Athlete.id,
        )
        .filter(KataGroupAthlete.kata_group_id == group.id)
        .all()
    )

    athletes = []

    for athlete in members:
        athlete_data = serialize_data(athlete)
        athlete_data["display_name"] = get_athlete_display_name(athlete)
        athletes.append(athlete_data)

    group_data = serialize_data(group)
    group_data["athletes"] = athletes
    group_data["athlete_count"] = len(athletes)
    group_data["is_complete"] = len(athletes) == 3

    return group_data


def validate_athlete_ids(db: Session, athlete_ids: list[int]):
    if len(athlete_ids) != len(set(athlete_ids)):
        raise HTTPException(
            status_code=422,
            detail="Один спортсмен не может повторяться в одной группе",
        )

    if len(athlete_ids) > 3:
        raise HTTPException(
            status_code=422,
            detail="В ката-группе может быть не более трёх спортсменов",
        )

    if not athlete_ids:
        return

    athletes = (
        db.query(Athlete)
        .filter(Athlete.id.in_(athlete_ids))
        .all()
    )

    found_ids = {athlete.id for athlete in athletes}
    missing_ids = set(athlete_ids) - found_ids

    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Спортсмены не найдены: {sorted(missing_ids)}",
        )


def check_duplicate_group(
    db: Session,
    athletes_ids: list[int],
    exclude_group_id: int | None = None
):
    selected_ids = sorted(set(athletes_ids))
    groups_query = db.query(KataGroup)
    if exclude_group_id is not None:
        groups_query = groups_query.filter(
            KataGroup.id != exclude_group_id
        )
    
    groups = groups_query.all()

    for group in groups:
        existing_ids = [
            row[0]
            for row in db.query(KataGroupAthlete.athlete_id)
            .filter(KataGroupAthlete.kata_group_id == group.id)
            .all()
        ]

        if sorted(existing_ids) == selected_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Группа уже существует.'
            )
    

@router.get("/fields")
def get_kata_group_fields():
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
        for column in inspect(KataGroup).columns
    ]


@router.get("/")
def get_kata_groups(db: Session = Depends(get_tournament_db)):
    groups = db.query(KataGroup).order_by(KataGroup.id.desc()).all()
    return [get_group_data(db, group) for group in groups]


@router.get("/{group_id}")
def get_kata_group(
    group_id: int,
    db: Session = Depends(get_tournament_db),
):
    db_group = db.get(KataGroup, group_id)

    if not db_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KataGroup not found",
        )

    return get_group_data(db, db_group)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_kata_group(
    data: dict[str, Any] = Body(...),
    db: Session = Depends(get_tournament_db),
):
    allowed_fields = set(serialize_data(KataGroup))
    unknown_fields = set(data.keys()) - allowed_fields - {"athlete_ids"}

    if unknown_fields:
        raise HTTPException(
            status_code=422,
            detail=f"Неизвестные поля: {sorted(unknown_fields)}",
        )

    name = str(data.get("name", "")).strip()
    category_id = data.get("category_id")
    athlete_ids = data.get("athlete_ids", [])

    if not name:
        raise HTTPException(
            status_code=422,
            detail="Название группы обязательно",
        )

    if not category_id:
        raise HTTPException(
            status_code=422,
            detail="Необходимо выбрать категорию",
        )

    if not isinstance(athlete_ids, list):
        raise HTTPException(
            status_code=422,
            detail="athlete_ids должен быть списком",
        )

    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Категория не найдена",
        )

    validate_athlete_ids(db, athlete_ids)

    check_duplicate_group(db, athlete_ids)
    group = KataGroup(
        name=name,
        category_id=category_id,
    )

    try:
        db.add(group)
        db.flush()

        for athlete_id in athlete_ids:
            db.add(
                KataGroupAthlete(
                    kata_group_id=group.id,
                    athlete_id=athlete_id,
                )
            )

        db.commit()
        db.refresh(group)

        return get_group_data(db, group)

    except Exception:
        db.rollback()
        raise


@router.put("/{group_id}")
def update_kata_group(
    group_id: int,
    data: dict[str, Any] = Body(...),
    db: Session = Depends(get_tournament_db),
):
    group = db.query(KataGroup).filter(
        KataGroup.id == group_id
    ).first()

    if not group:
        raise HTTPException(
            status_code=404,
            detail="Ката-группа не найдена",
        )

    allowed_fields = set(serialize_data(KataGroup))
    unknown_fields = set(data.keys()) - allowed_fields - {"athlete_ids"}

    if unknown_fields:
        raise HTTPException(
            status_code=422,
            detail=f"Неизвестные поля: {sorted(unknown_fields)}",
        )

    if "name" in data:
        name = str(data["name"]).strip()

        if not name:
            raise HTTPException(
                status_code=422,
                detail="Название группы не может быть пустым",
            )

        group.name = name

    if "category_id" in data:
        category = db.query(Category).filter(
            Category.id == data["category_id"]
        ).first()

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Категория не найдена",
            )

        group.category_id = data["category_id"]

    try:
        if "athlete_ids" in data:
            athlete_ids = data["athlete_ids"]

            if not isinstance(athlete_ids, list):
                raise HTTPException(
                    status_code=422,
                    detail="athlete_ids должен быть списком",
                )

            validate_athlete_ids(db, athlete_ids)
            check_duplicate_group(db, athlete_ids, group_id)

            db.query(KataGroupAthlete).filter(
                KataGroupAthlete.kata_group_id == group.id
            ).delete(synchronize_session=False)

            for athlete_id in athlete_ids:
                db.add(
                    KataGroupAthlete(
                        kata_group_id=group.id,
                        athlete_id=athlete_id,
                    )
                )

        db.commit()
        db.refresh(group)

        return get_group_data(db, group)

    except Exception:
        db.rollback()
        raise


@router.post("/{group_id}")
def validate_kata_group(
    group_id: int,
    db: Session = Depends(get_tournament_db),
):
    group = db.query(KataGroup).filter(
        KataGroup.id == group_id
    ).first()

    if not group:
        raise HTTPException(
            status_code=404,
            detail="Ката-группа не найдена",
        )

    count = db.query(KataGroupAthlete).filter(
        KataGroupAthlete.kata_group_id == group_id
    ).count()

    if count != 3:
        raise HTTPException(
            status_code=422,
            detail=f"В группе должно быть ровно 3 спортсмена. Сейчас: {count}",
        )

    return {
        "valid": True,
        "message": "Состав ката-группы корректен",
        "athlete_count": count,
    }


@router.delete("/{group_id}")
def delete_kata_group(
    group_id: int,
    db: Session = Depends(get_tournament_db),
):
    group = db.query(KataGroup).filter(
        KataGroup.id == group_id
    ).first()

    if not group:
        raise HTTPException(
            status_code=404,
            detail="Ката-группа не найдена",
        )

    try:
        db.delete(group)
        db.commit()

        return {"message": "Ката-группа удалена"}

    except Exception:
        db.rollback()
        raise