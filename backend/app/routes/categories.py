from datetime import date
from decimal import Decimal
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, inspect

from app.tournament_database import get_tournament_db
from app.tournament_models import Category, Athlete, AthleteCategory
from app.models import Tournament
from app.database import get_db

router = APIRouter(
    prefix="/api/tournaments/{tournament_id}/categories",
    tags=["Categories"]
)

def serialize_category(category: Category) -> dict[str, Any]:
    return {
        column.key: getattr(category, column.key)
        for column in inspect(Category).columns
    }

def validate_category_data(data: dict[str, any]) -> dict[str, Any]:
    columns = {
        column.key
        for column in inspect(Category).columns
    }
    protected = {"id"}
    allowed = columns - protected

    unknown = set(data.keys()) - allowed
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Неизвестное поле: {', '.join(sorted(unknown))}"
        )
    return data

def get_tournament_start_date(
        tournament_id: int,
        main_db: Session = Depends(get_db),
) -> date:
    tournament = main_db.get(Tournament, tournament_id)

    if tournament is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found"
        )

    return tournament.start_date

def get_athlete_value(
        athlete: Athlete,
        names: tuple[str, ...]
):
    columns = {
        column.key
        for column in inspect(Athlete).columns
    }
    for name in names:
        if name in columns:
            return getattr(athlete, name)
        
    return None

def calculate_age(
        birth_date: date,
        tournament_date: date
) -> int:
    return (
        tournament_date.year - birth_date.year
        - (
            (tournament_date.month, tournament_date.day - 1)
            < (birth_date.month, birth_date.day)
        )
    )

@router.get("/fields")
def get_category_fields(db: Session = Depends(get_tournament_db)):
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
        for column in inspect(Category).columns
    ]

@router.get("/")
def get_categories(db: Session = Depends(get_tournament_db)):
    categories = db.query(Category).order_by(Category.id.desc()).all()
    return [serialize_category(item) for item in categories]

@router.get("/distribution-preview")
def distribution_preview(
    tournament_id: int,
    db: Session = Depends(get_tournament_db),
    main_db: Session = Depends(get_db),
):
    print('h')
    tournament_date = get_tournament_start_date(tournament_id, main_db)

    athletes = db.query(Athlete).order_by(Athlete.id).all()
    categories = db.query(Category).order_by(Category.id).all()

    result = []
    for athlete in athletes:
        birth_date = get_athlete_value(
            athlete,
            ("birth_date", "date_of_birth", "dob"),
        )
        gender = get_athlete_value(athlete, ("gender",))
        weight = get_athlete_value(athlete, ("weight",))

        if not birth_date:
            result.append({
                "athlete_id": athlete.id,
                "status": "missing_birth_date",
                "suggestions": [],
            })
            continue

        age = calculate_age(birth_date, tournament_date)
        suggestions = []

        for category in categories:
            if category.gender != gender:
                continue

            if not category.age_min <= age <= category.age_max:
                continue

            if category.discipline == "kumite":
                if weight is None:
                    continue

                if not (
                    category.weight_min
                    <= Decimal(str(weight))
                    <= category.weight_max
                ):
                    continue

            suggestions.append({
                "category_id": category.id,
                "category_name": category.name,
                "discipline": category.discipline,
            })

        result.append({
            "athlete_id": athlete.id,
            "age": age,
            "status": "matched" if suggestions else "no_matching_category",
            "suggestions": suggestions,
        })

    return {
        "competition_date": tournament_date,
        "athletes": result,
    }

@router.get("/{category_id}")
def get_category(
    category_id: int,
    db: Session = Depends(get_tournament_db)
):
    db_category = db.get(Category, category_id)

    if db_category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return serialize_category(db_category)

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_category(
    data: dict[str, Any],
    db: Session = Depends(get_tournament_db)
):
    db_category = Category(**validate_category_data(data))

    db.add(db_category)
    db.commit()
    db.refresh(db_category)

    return serialize_category(db_category)

@router.put("/{category_id}")
def update_category(
    category_id: int,
    data: dict[str, Any],
    db: Session = Depends(get_tournament_db)
):
    db_category = db.get(Category, category_id)

    if db_category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    category_data = validate_category_data(data)
    for key, value in category_data.items():
        setattr(db_category, key, value)

    db.commit()
    db.refresh(db_category)

    return serialize_category(db_category)

@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_tournament_db)
):
    db_category = db.get(Category, category_id)
    
    if db_category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    db.query(AthleteCategory).filter(
        AthleteCategory.category_id == category_id
    ).delete(synchronize_session=False)

    db.delete(db_category)
    db.commit()



@router.post("/assign")
def assign_athletes(
    tournament_id: int,
    assignments: list[dict[str, int]],
    db: Session = Depends(get_tournament_db),
    main_db: Session = Depends(get_db),
):
    # Повторно проверяем соответствие категориям перед записью.
    preview = distribution_preview(
        tournament_id=tournament_id,
        db=db,
        central_db=main_db,
    )

    allowed = {
        (item["athlete_id"], suggestion["category_id"])
        for item in preview["athletes"]
        for suggestion in item["suggestions"]
    }

    created = 0

    for item in assignments:
        athlete_id = item.get("athlete_id")
        category_id = item.get("category_id")

        if (athlete_id, category_id) not in allowed:
            raise HTTPException(
                422,
                f"Атлет {athlete_id} не подходит для категории {category_id}",
            )

        exists = db.query(AthleteCategory).filter(
            AthleteCategory.athlete_id == athlete_id,
            AthleteCategory.category_id == category_id,
        ).first()

        if not exists:
            db.add(
                AthleteCategory(
                    athlete_id=athlete_id,
                    category_id=category_id,
                )
            )
            created += 1

    db.commit()

    return {"created": created}