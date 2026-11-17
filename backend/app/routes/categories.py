from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.tournament_database import get_tournament_db
from app.models import Tournament
from app.tournament_models import (
    Category,
    Athlete,
    KataGroup,
    KataGroupAthlete,
    CategoryDistribution,
    Undistribution,
)


router = APIRouter(
    prefix="/api/tournaments/{tournament_id}/categories",
    tags=["Categories"]
)


# ============================================================
# ОБЩИЕ ФУНКЦИИ
# ============================================================

def serialize_model(obj) -> dict[str, Any]:
    return {
        column.key: getattr(obj, column.key)
        for column in inspect(obj.__class__).columns
    }


def get_model_fields(model, hidden_fields=None):
    hidden_fields = hidden_fields or {"id"}

    result = []

    for column in inspect(model).columns:
        if column.key in hidden_fields:
            continue

        result.append({
            "name": column.key,
            "type": str(column.type),
            "nullable": column.nullable,
            "required": (
                not column.nullable
                and column.default is None
                and column.server_default is None
            )
        })

    return result


def get_tournament_start_date(
    tournament_id: int,
    main_db: Session
) -> date:
    tournament = main_db.get(Tournament, tournament_id)

    if tournament is None:
        raise HTTPException(
            status_code=404,
            detail="Турнир не найден"
        )

    if not tournament.start_date:
        raise HTTPException(
            status_code=400,
            detail="У турнира не указана дата начала"
        )

    return tournament.start_date


def get_reference_date(tournament_date: date) -> date:
    return tournament_date - timedelta(days=1)


def parse_date(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None

    return None


def calculate_age(birth_date: date, reference_date: date) -> int:
    return (
        reference_date.year
        - birth_date.year
        - (
            (reference_date.month, reference_date.day)
            < (birth_date.month, birth_date.day)
        )
    )


def get_athlete_age(athlete, reference_date: date):
    birth_date = None

    for field in ("birth_date", "date_of_birth", "dob"):
        if hasattr(athlete, field):
            birth_date = parse_date(getattr(athlete, field))
            if birth_date:
                break

    if birth_date:
        return calculate_age(birth_date, reference_date)

    stored_age = getattr(athlete, "age_at_tournament", None)

    if stored_age is not None:
        return int(stored_age)

    return None


def get_age_group(age: int):
    if 8 <= age <= 9:
        return "8-9"

    if 10 <= age <= 11:
        return "10-11"

    if 12 <= age <= 13:
        return "12-13"

    if 14 <= age <= 15:
        return "14-15"

    if 16 <= age <= 17:
        return "16-17"

    if age >= 18:
        return "18+"

    return None


def normalize_gender(value):
    if value is None:
        return None

    return str(value).strip().lower()


def normalize_discipline(value):
    if value is None:
        return ""

    return str(value).strip().lower()


def is_kata_group_category(category) -> bool:
    name = str(getattr(category, "name", "")).strip().lower()
    discipline = normalize_discipline(
        getattr(category, "discipline", "")
    )

    return (
        name.startswith("ката-группа")
        or discipline in (
            "kata_group",
            "kata-group",
            "team_kata",
            "team kata"
        )
    )


def category_matches_gender(category, athlete_gender) -> bool:
    category_gender = normalize_gender(
        getattr(category, "gender", None)
    )

    athlete_gender = normalize_gender(athlete_gender)

    if category_gender in ("unisex", "mixed", "общая"):
        return True

    return category_gender == athlete_gender


def category_matches_age(category, age: int) -> bool:
    age_min = getattr(category, "age_min", None)
    age_max = getattr(category, "age_max", None)

    if age_min is not None and age < age_min:
        return False

    if age_max is not None and age > age_max:
        return False

    return True


def category_matches_weight(category, weight) -> bool:
    if weight is None:
        return False

    try:
        weight = Decimal(str(weight))
    except (InvalidOperation, ValueError):
        return False

    weight_min = getattr(category, "weight_min", None)
    weight_max = getattr(category, "weight_max", None)

    if weight_min is not None and weight < Decimal(str(weight_min)):
        return False

    if weight_max is not None and weight > Decimal(str(weight_max)):
        return False

    return True


def get_athlete_categories(
    athlete,
    categories,
    age,
    gender,
    weight
):
    suggestions = []

    for category in categories:

        if is_kata_group_category(category):
            continue

        discipline = normalize_discipline(category.discipline)

        if discipline not in ("kata", "kumite"):
            continue

        if not category_matches_age(category, age):
            continue

        if not category_matches_gender(category, gender):
            continue

        if discipline == "kumite":
            if not category_matches_weight(category, weight):
                continue

        suggestions.append({
            "category_id": category.id,
            "category_name": category.name,
            "discipline": discipline
        })

    return suggestions


# ============================================================
# ПРЕДВАРИТЕЛЬНЫЙ ПРОСМОТР
# ============================================================

def build_distribution_preview(
    tournament_id: int,
    db: Session,
    main_db: Session
):
    tournament_date = get_tournament_start_date(
        tournament_id,
        main_db
    )

    reference_date = get_reference_date(tournament_date)

    athletes = db.query(Athlete).order_by(Athlete.id).all()
    categories = db.query(Category).order_by(Category.id).all()

    result = []

    for athlete in athletes:

        age = get_athlete_age(athlete, reference_date)

        gender = getattr(athlete, "gender", None)
        weight = getattr(athlete, "weight", None)

        athlete_data = {
            "athlete_id": athlete.id,
            "athlete_name": " ".join(
                str(getattr(athlete, field, "") or "").strip()
                for field in (
                    "last_name",
                    "first_name",
                    "second_name"
                )
            ).strip(),
            "age": age,
            "gender": gender,
            "weight": weight,
            "suggestions": [],
            "status": "matched",
            "reason": None
        }

        if age is None:
            athlete_data["status"] = "undistributed"
            athlete_data["reason"] = "Не удалось определить возраст"
            result.append(athlete_data)
            continue

        athlete_data["age_group"] = get_age_group(age)

        if athlete_data["age_group"] is None:
            athlete_data["status"] = "undistributed"
            athlete_data["reason"] = "Возраст не входит в допустимые группы"
            result.append(athlete_data)
            continue

        suggestions = get_athlete_categories(
            athlete,
            categories,
            age,
            gender,
            weight
        )

        athlete_data["suggestions"] = suggestions

        if not suggestions:
            athlete_data["status"] = "undistributed"
            athlete_data["reason"] = (
                "Не найдена подходящая категория по возрасту, "
                "полу и весу"
            )

        result.append(athlete_data)

    # --------------------------------------------------------
    # КАТА-ГРУППЫ
    # --------------------------------------------------------

    groups = db.query(KataGroup).order_by(KataGroup.id).all()

    group_results = []

    group_categories = [
        category
        for category in categories
        if is_kata_group_category(category)
    ]

    for group in groups:

        members = (
            db.query(Athlete)
            .join(
                KataGroupAthlete,
                KataGroupAthlete.athlete_id == Athlete.id
            )
            .filter(
                KataGroupAthlete.kata_group_id == group.id
            )
            .order_by(Athlete.id)
            .all()
        )

        member_ages = [
            get_athlete_age(member, reference_date)
            for member in members
        ]

        group_data = {
            "kata_group_id": group.id,
            "name": group.name,
            "athlete_ids": [member.id for member in members],
            "athlete_count": len(members),
            "category_id": None,
            "category_name": None,
            "status": "matched",
            "reason": None
        }

        if len(members) != 3:
            group_data["status"] = "undistributed"
            group_data["reason"] = (
                f"В ката-группе должно быть 3 спортсмена. "
                f"Сейчас: {len(members)}"
            )
            group_results.append(group_data)
            continue

        if any(age is None for age in member_ages):
            group_data["status"] = "undistributed"
            group_data["reason"] = "Не удалось определить возраст участника"
            group_results.append(group_data)
            continue

        age_groups = {
            get_age_group(age)
            for age in member_ages
        }

        if None in age_groups or len(age_groups) != 1:
            group_data["status"] = "undistributed"
            group_data["reason"] = (
                "Все три спортсмена должны относиться "
                "к одной возрастной группе"
            )
            group_results.append(group_data)
            continue

        age_group = next(iter(age_groups))
        expected_category_name = f"Ката-группа {age_group}"

        matching_categories = [
            category
            for category in group_categories
            if str(category.name).strip().casefold()
            == expected_category_name.casefold()
        ]

        if len(matching_categories) == 0:
            group_data["status"] = "undistributed"
            group_data["reason"] = (
                f"Не найдена категория «{expected_category_name}»"
            )
            group_results.append(group_data)
            continue

        if len(matching_categories) > 1:
            group_data["status"] = "undistributed"
            group_data["reason"] = (
                f"Найдено несколько категорий «{expected_category_name}»"
            )
            group_results.append(group_data)
            continue

        category = matching_categories[0]

        group_data["category_id"] = category.id
        group_data["category_name"] = category.name
        group_data["age_group"] = age_group

        group_results.append(group_data)

    return {
        "tournament_date": tournament_date,
        "age_reference_date": reference_date,
        "athletes": result,
        "kata_groups": group_results
    }


@router.get("/distribution-preview")
def distribution_preview(
    tournament_id: int,
    db: Session = Depends(get_tournament_db),
    main_db: Session = Depends(get_db)
):
    return build_distribution_preview(
        tournament_id,
        db,
        main_db
    )


# ============================================================
# АВТОМАТИЧЕСКОЕ РАСПРЕДЕЛЕНИЕ
# ============================================================

@router.post("/distribute")
def distribute_athletes(
    tournament_id: int,
    db: Session = Depends(get_tournament_db),
    main_db: Session = Depends(get_db)
):
    try:
        preview = build_distribution_preview(
            tournament_id,
            db,
            main_db
        )

        new_distribution = []
        new_undistributed = []
        invalid_groups = []

        # ----------------------------------------------------
        # ИНДИВИДУАЛЬНЫЕ ДИСЦИПЛИНЫ
        # ----------------------------------------------------

        for athlete in preview["athletes"]:

            suggestions = athlete["suggestions"]

            by_discipline = {
                "kata": [],
                "kumite": []
            }

            for suggestion in suggestions:
                discipline = suggestion["discipline"]

                if discipline in by_discipline:
                    by_discipline[discipline].append(suggestion)

            assigned_disciplines = []

            for discipline, options in by_discipline.items():

                if len(options) == 1:
                    new_distribution.append({
                        "category_id": options[0]["category_id"],
                        "athlete_id": athlete["athlete_id"],
                        "kata_group_id": None
                    })

                    assigned_disciplines.append(discipline)

                elif len(options) > 1:
                    # Не выбираем произвольную категорию.
                    # При неоднозначности оставляем спортсмена
                    # нераспределённым по этой дисциплине.
                    continue

            if not assigned_disciplines:
                reason = athlete["reason"]

                if suggestions:
                    reason = (
                        "Найдено несколько подходящих категорий "
                        "в одной или нескольких дисциплинах"
                    )

                new_undistributed.append({
                    "athlete_id": athlete["athlete_id"],
                    "reason": reason or "Не найдена подходящая категория"
                })

        # ----------------------------------------------------
        # КАТА-ГРУППЫ
        # ----------------------------------------------------

        for group in preview["kata_groups"]:

            if group["status"] != "matched":
                invalid_groups.append({
                    "kata_group_id": group["kata_group_id"],
                    "name": group["name"],
                    "reason": group["reason"]
                })
                continue

            new_distribution.append({
                "category_id": group["category_id"],
                "athlete_id": None,
                "kata_group_id": group["kata_group_id"]
            })

        # ----------------------------------------------------
        # ЗАМЕНА СТАРОГО РАСПРЕДЕЛЕНИЯ
        # ----------------------------------------------------

        db.query(CategoryDistribution).delete(
            synchronize_session=False
        )

        db.query(Undistribution).delete(
            synchronize_session=False
        )

        db.flush()

        for item in new_distribution:
            db.add(CategoryDistribution(**item))

        for item in new_undistributed:
            db.add(Undistribution(**item))

        db.commit()

        return {
            "message": "Распределение выполнено",
            "distributed_athletes": sum(
                1
                for item in new_distribution
                if item["athlete_id"] is not None
            ),
            "distributed_kata_groups": sum(
                1
                for item in new_distribution
                if item["kata_group_id"] is not None
            ),
            "undistributed_athletes": len(new_undistributed),
            "invalid_kata_groups": invalid_groups,
            "details": {
                "distribution": new_distribution,
                "undistributed": new_undistributed
            }
        }

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Ошибка базы данных при распределении: {str(error)}"
        )

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Ошибка распределения: {str(error)}"
        )


# ============================================================
# ПРОСМОТР РАСПРЕДЕЛЕНИЯ
# ============================================================

@router.get("/distribution")
def get_distribution(
    tournament_id: int,
    db: Session = Depends(get_tournament_db)
):
    categories = db.query(Category).order_by(Category.id).all()

    result = []

    for category in categories:

        records = (
            db.query(CategoryDistribution)
            .filter(
                CategoryDistribution.category_id == category.id
            )
            .all()
        )

        participants = []

        for record in records:

            if record.athlete_id is not None:
                athlete = db.get(Athlete, record.athlete_id)

                if athlete:
                    participants.append(serialize_model(athlete))

            elif record.kata_group_id is not None:
                group = db.get(KataGroup, record.kata_group_id)

                if group:
                    group_data = serialize_model(group)

                    members = (
                        db.query(Athlete)
                        .join(
                            KataGroupAthlete,
                            KataGroupAthlete.athlete_id == Athlete.id
                        )
                        .filter(
                            KataGroupAthlete.kata_group_id == group.id
                        )
                        .order_by(Athlete.id)
                        .all()
                    )

                    group_data["athletes"] = [
                        serialize_model(member)
                        for member in members
                    ]

                    group_data["athlete_count"] = len(members)

                    participants.append(group_data)

        result.append({
            "category_id": category.id,
            "category_name": category.name,
            "discipline": getattr(category, "discipline", None),
            "participants": participants,
            "participants_count": len(participants),
        })

    undistributed_records = (
        db.query(Undistribution).all()
    )

    undistributed = []

    for record in undistributed_records:
        athlete = db.get(Athlete, record.athlete_id)

        if athlete:
            item = serialize_model(athlete)
            item["reason"] = record.reason
            undistributed.append(item)

    return {
        "categories": result,
        "undistributed": undistributed,
        "undistributed_count": len(undistributed)
    }


# ============================================================
# СПИСОК НЕРАСПРЕДЕЛЁННЫХ
# ============================================================

@router.get("/undistributed")
def get_undistributed(
    tournament_id: int,
    db: Session = Depends(get_tournament_db)
):
    records = db.query(Undistribution).all()

    result = []

    for record in records:
        athlete = db.get(Athlete, record.athlete_id)

        if athlete:
            item = serialize_model(athlete)
            item["reason"] = record.reason
            result.append(item)

    return result


# ============================================================
# ПОЛЯ КАТЕГОРИЙ
# ============================================================

@router.get("/fields")
def get_category_fields(
    tournament_id: int,
    db: Session = Depends(get_tournament_db)
):
    return get_model_fields(Category)

# ============================================================
# ПОЛУЧЕНИЕ АТЛЕТОВ КАТЕГОРИИ
# ============================================================

@router.get("/{category_id}/athletes")
def get_category_athletes(
    tournament_id: int,
    category_id: int,
    db: Session = Depends(get_tournament_db)
):
    category = db.get(Category, category_id)

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Категория не найдена"
        )
    
    distributions = (
        db.query(CategoryDistribution)
        .filter(CategoryDistribution.category_id == category_id)
        .all()
    )

    participants = []

    for item in distributions:
        if item.athlete_id is not None:
            athlete = db.query(Athlete).filter(
                Athlete.id == item.athlete_id
            ).first()

            if athlete:
                data = serialize_model(athlete)
        elif item.kata_group_id is not None:
            group = db.query(KataGroup).filter(
                KataGroup.id == item.kata_group_id
            ).first()

            if group:
                data = serialize_model(group)
                members = (
                    db.query(Athlete)
                    .join(
                        KataGroupAthlete,
                        KataGroupAthlete.athlete_id == Athlete.id
                    )
                    .filter(
                        KataGroupAthlete.kata_group_id == group.id
                    )
                    .all()
                )
                data["athletes"] = [
                    serialize_model(athlete)
                    for athlete in members
                ]
                
        participants.append(data)
        
    return {
        "category": serialize_model(category),
        "participants": participants,
        "count": len(participants)
    }

# ============================================================
# CRUD КАТЕГОРИЙ
# ============================================================

def validate_category_data(data: dict[str, Any]):
    columns = {
        column.key
        for column in inspect(Category).columns
    }

    allowed = columns - {"id"}
    unknown = set(data.keys()) - allowed

    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Неизвестные поля: {', '.join(sorted(unknown))}"
        )

    return data


@router.get("/")
def get_categories(
    tournament_id: int,
    db: Session = Depends(get_tournament_db)
):
    categories = db.query(Category).order_by(Category.id).all()

    return [
        serialize_model(category)
        for category in categories
    ]


@router.get("/{category_id}")
def get_category(
    tournament_id: int,
    category_id: int,
    db: Session = Depends(get_tournament_db)
):
    category = db.get(Category, category_id)

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Категория не найдена"
        )

    return serialize_model(category)


@router.post("/")
def create_category(
    tournament_id: int,
    data: dict[str, Any] = Body(...),
    db: Session = Depends(get_tournament_db)
):
    data = validate_category_data(data)

    category = Category(**data)

    try:
        db.add(category)
        db.commit()
        db.refresh(category)

        return serialize_model(category)

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Не удалось создать категорию: {e}"
        )


@router.put("/{category_id}")
def update_category(
    tournament_id: int,
    category_id: int,
    data: dict[str, Any] = Body(...),
    db: Session = Depends(get_tournament_db)
):
    category = db.get(Category, category_id)

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Категория не найдена"
        )

    data = validate_category_data(data)

    try:
        for key, value in data.items():
            setattr(category, key, value)

        db.commit()
        db.refresh(category)

        return serialize_model(category)

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Не удалось обновить категорию"
        )


@router.delete("/{category_id}")
def delete_category(
    tournament_id: int,
    category_id: int,
    db: Session = Depends(get_tournament_db)
):
    category = db.get(Category, category_id)

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Категория не найдена"
        )

    try:
        db.delete(category)
        db.commit()

        return {
            "message": "Категория удалена",
            "category_id": category_id
        }

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Не удалось удалить категорию"
        )