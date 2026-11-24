from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from sqlalchemy.orm import Session, joinedload

from app.tournament_database import get_tournament_db
from app.tournament_models import (
    Athlete,
    BronzeMatchResult,
    Category,
    CategoryDistribution,
    CategoryTatami,
    Club,
    KataCompetition,
    KataRound,
    KataRoundParticipant,
    KataScore,
    Result,
    KataTatami,
    KumiteDrawEntry,
    KumiteDrawMatch,
    
)


router = APIRouter(
    prefix="/api/tournaments/{tournament_id}/result",
    tags=["Results"]
)

# =========================================================
# RESULTS
# =========================================================

def serialize_result(result: Result):
    athlete = result.athlete

    return {
        "id": result.id,
        "athlete_id": athlete.id,
        "full_name": f'{athlete.first_name} {athlete.last_name}',
        "club": (
            athlete.club.name
            if athlete.club
            else None
        ),
        "place": result.place
    }
# =========================================================
# HELPERS
# =========================================================

def category_matches(db: Session, category_id: int):
    return (
        db.query(KumiteDrawMatch)
        .filter(KumiteDrawMatch.category_id == category_id)
        .order_by(
            KumiteDrawMatch.round_number,
            KumiteDrawMatch.match_number
        )
        .all()
    )
# =========================================================
# RESULTS CALCULATION
# =========================================================

def get_category_athlete_ids(db: Session, category_id: int):
    entries = db.query(KumiteDrawEntry).filter(
        KumiteDrawEntry.category_id == category_id
    ).all()

    athlete_ids = {
        entry.athlete_id for entry in entries
    }

    if not athlete_ids:
        for match in category_matches(db, category_id):
            if match.athlete1_id:
                athlete_ids.add(match.athlete1_id)

            if match.athlete2_id:
                athlete_ids.add(match.athlete2_id)

    return athlete_ids

def finalize_category(db: Session, category_id: int) -> bool:
    """
    Определяет и сохраняет результаты категории.
    Вызывается после завершения обычного боя или боя за третье место.
    """

    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if not category:
        return False

    matches = category_matches(db, category_id)

    if not matches:
        return False

    athlete_ids = get_category_athlete_ids(
        db,
        category_id
    )

    if len(athlete_ids) < 2:
        return False

    # Все реальные бои сетки должны быть завершены.
    unfinished = [
        match for match in matches
        if match.status not in ("completed", "bye")
    ]

    if unfinished:
        return False

    if len(athlete_ids) == 2:
        results = determine_two_athlete_results(
            matches,
            athlete_ids
        )

    elif len(athlete_ids) == 3:
        results = determine_round_robin_results(
            matches,
            athlete_ids
        )

    else:
        results = determine_olympic_results(
            db,
            category_id,
            matches
        )

    if not results:
        return False

    result_ids = [
        item["athlete_id"]
        for item in results
    ]

    if len(result_ids) != len(set(result_ids)):
        return False

    if not set(result_ids).issubset(athlete_ids):
        return False

    db.query(Result).filter(
        Result.category_id == category_id
    ).delete(synchronize_session=False)

    for item in results:
        db.add(
            Result(
                category_id=category_id,
                athlete_id=item["athlete_id"],
                place=item["place"]
            )
        )

    db.flush()

    return True

def determine_olympic_results(
    db: Session,
    category_id: int,
    matches
):
    real_matches = [
        match for match in matches
        if match.athlete1_id is not None
        and match.athlete2_id is not None
    ]

    if not real_matches:
        return None

    final_round = max(
        match.round_number for match in real_matches
    )

    finals = [
        match for match in real_matches
        if match.round_number == final_round
    ]

    if len(finals) != 1:
        return None

    final = finals[0]

    if final.status != "completed":
        return None

    winner_id = final.winner_athlete_id

    if winner_id == final.athlete1_id:
        second_place = final.athlete2_id
    elif winner_id == final.athlete2_id:
        second_place = final.athlete1_id
    else:
        return None

    bronze = db.query(BronzeMatchResult).filter(
        BronzeMatchResult.category_id == category_id
    ).first()

    if not bronze or bronze.status != "completed":
        return None

    if not bronze.winner_athlete_id:
        return None

    return [
        {"athlete_id": winner_id, "place": 1},
        {"athlete_id": second_place, "place": 2},
        {"athlete_id": bronze.winner_athlete_id, "place": 3},
    ]

def determine_round_robin_results(matches, athlete_ids):
    if len(athlete_ids) != 3:
        return None

    athlete_ids = list(athlete_ids)

    wins = {
        athlete_id: 0
        for athlete_id in athlete_ids
    }

    completed = [
        match for match in matches
        if match.status == "completed"
        and match.athlete1_id is not None
        and match.athlete2_id is not None
        and match.winner_athlete_id is not None
    ]

    expected_pairs = {
        frozenset((athlete_ids[0], athlete_ids[1])),
        frozenset((athlete_ids[0], athlete_ids[2])),
        frozenset((athlete_ids[1], athlete_ids[2]))
    }

    actual_pairs = {
        frozenset((match.athlete1_id, match.athlete2_id))
        for match in completed
    }

    if len(completed) != 3 or actual_pairs != expected_pairs:
        return None

    for match in completed:
        if match.winner_athlete_id not in wins:
            return None

        wins[match.winner_athlete_id] += 1

    ranking = sorted(
        athlete_ids,
        key=lambda athlete_id: wins[athlete_id],
        reverse=True
    )

    if len(set(wins.values())) != 3:
        return None

    return [
        {"athlete_id": ranking[0], "place": 1},
        {"athlete_id": ranking[1], "place": 2},
        {"athlete_id": ranking[2], "place": 3},
    ]

def determine_two_athlete_results(matches, athlete_ids):
    final = next(
        (
            match for match in matches
            if match.athlete1_id in athlete_ids
            and match.athlete2_id in athlete_ids
            and match.status == "completed"
        ),
        None
    )

    if not final:
        return None

    winner_id = final.winner_athlete_id

    if winner_id == final.athlete1_id:
        loser_id = final.athlete2_id
    elif winner_id == final.athlete2_id:
        loser_id = final.athlete1_id
    else:
        return None

    return [
        {"athlete_id": winner_id, "place": 1},
        {"athlete_id": loser_id, "place": 2},
    ]



@router.get("/")
def get_competition_results(
    db: Session = Depends(get_tournament_db)
):
    results = (
        db.query(Result)
        .options(
            joinedload(Result.athlete).joinedload(
                Athlete.club
            ),
            joinedload(Result.category)
        )
        .order_by(
            Result.category_id,
            Result.place
        )
        .all()
    )

    grouped = {}

    for result in results:
        if not result.athlete or not result.category:
            continue

        category_id = result.category_id

        if category_id not in grouped:
            grouped[category_id] = {
                "category_id": category_id,
                "category_name": result.category.name,
                "results": []
            }

        grouped[category_id]["results"].append(
            serialize_result(result)
        )

    return list(grouped.values())


@router.get("/{category_id}")
def get_category_results(
    category_id: int,
    db: Session = Depends(get_tournament_db)
):
    results = (
        db.query(Result)
        .options(
            joinedload(Result.athlete).joinedload(
                Athlete.club
            )
        )
        .filter(Result.category_id == category_id)
        .order_by(Result.place)
        .all()
    )

    return [
        serialize_result(result)
        for result in results
        if result.athlete
    ]


@router.post("/{category_id}/finalize")
def finalize_category_endpoint(
    category_id: int,
    db: Session = Depends(get_tournament_db)
):
    try:
        saved = finalize_category(db, category_id)

        if not saved:
            db.rollback()
            return {
                "success": False,
                "message": "Категория ещё не готова к фиксации результатов"
            }

        db.commit()

        return {
            "success": True,
            "message": "Результаты категории сохранены"
        }

    except Exception:
        db.rollback()
        raise