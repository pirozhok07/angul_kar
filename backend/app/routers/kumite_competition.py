from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from ..tournament_database_ import get_tournament_db
from ..tournament_models import (
    Category,
    Athlete,
    KumiteDrawEntry,
    KumiteDrawMatch,
    Result,
    KumiteTatami,
    CategoryTatami,
    BronzeMatchResult,
)

router = APIRouter(
    prefix="/api/tournaments/{tournament_id}/kumite-competition",
    tags=["Kuumite Competition"]
)


# =========================================================
# SCHEMAS
# =========================================================

class TatamiRequest(BaseModel):
    count: int


class CategoryAssignment(BaseModel):
    category_id: int
    tatami_id: Optional[int] = None


class AssignmentsRequest(BaseModel):
    assignments: list[CategoryAssignment]


class BronzeWinnerRequest(BaseModel):
    winner_athlete_id: int


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


def athlete_name(athlete):
    if not athlete:
        return None

    return f"{athlete.last_name} {athlete.first_name}"


def get_loser(match):
    if match.status != "completed":
        return None

    if match.winner_athlete_id == match.athlete1_id:
        return match.athlete2_id

    if match.winner_athlete_id == match.athlete2_id:
        return match.athlete1_id

    return None


def get_round_label(round_number: int, max_round: int):
    if round_number == max_round:
        return "Финал"

    if round_number == max_round - 1:
        return "Полуфинал"

    denominator = 2 ** (max_round - round_number)

    return f"1/{denominator}"


def get_round_phase(round_number: int, max_round: int):
    return 2 ** (max_round - round_number)


def build_bout(
    category: Category,
    match: KumiteDrawMatch,
    max_round: int
):
    return {
        "category_id": category.id,
        "category_name": category.name,
        "match_id": match.id,
        "bronze_match_id": None,
        "match_number": match.match_number,
        "round_number": match.round_number,
        "round_count": max_round,
        "bout_type": (
            "final" if match.round_number == max_round else "regular"
        ),
        "stage": get_round_label(match.round_number, max_round),
        "phase_order": (
            0 if match.round_number == max_round
            else get_round_phase(match.round_number, max_round)
        ),
        "athlete1_id": match.athlete1_id,
        "athlete2_id": match.athlete2_id,
        "athlete1": athlete_name(match.athlete1),
        "athlete2": athlete_name(match.athlete2),
        "winner_athlete_id": match.winner_athlete_id,
        "status": match.status,
    }


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


# =========================================================
# TATAMI SETTINGS
# =========================================================

@router.get("/tatamis")
def get_tatamis(db: Session = Depends(get_tournament_db)):
    tatamis = (
        db.query(KumiteTatami)
        .order_by(KumiteTatami.number)
        .all()
    )

    return [
        {
            "id": item.id,
            "name": item.name,
            "number": item.number
        }
        for item in tatamis
    ]


@router.put("/tatamis")
def set_tatamis(
    data: TatamiRequest,
    db: Session = Depends(get_tournament_db)
):
    if data.count < 1 or data.count > 20:
        raise HTTPException(
            status_code=400,
            detail="Количество татами должно быть от 1 до 20"
        )

    existing = (
        db.query(KumiteTatami)
        .order_by(KumiteTatami.number)
        .all()
    )

    for tatami in existing:
        if tatami.number > data.count:
            used = db.query(KumiteTatami).filter(
                KumiteTatami.tatami_id == tatami.id
            ).first()

            if used:
                raise HTTPException(
                    status_code=400,
                    detail=f"{tatami.name} назначено категориям"
                )

    for tatami in existing:
        if tatami.number > data.count:
            db.delete(tatami)

    db.flush()

    existing_numbers = {
        item.number
        for item in db.query(KumiteTatami).all()
    }

    for number in range(1, data.count + 1):
        if number not in existing_numbers:
            db.add(
                KumiteTatami(
                    name=f"Татами {number}",
                    number=number
                )
            )

    db.commit()

    return get_tatamis(db)


# =========================================================
# CATEGORY ASSIGNMENTS
# =========================================================

@router.get("/assignments")
def get_assignments(db: Session = Depends(get_tournament_db)):
    categories = (
        db.query(Category)
        .filter(Category.discipline == "kumite")
        .order_by(Category.name)
        .all()
    )

    assignments = db.query(CategoryTatami).all()

    assignment_map = {
        item.category_id: item.kumite_tatami_id
        for item in assignments
    }

    return [
        {
            "category_id": category.id,
            "category_name": category.name,
            "tatami_id": assignment_map.get(category.id)
        }
        for category in categories
    ]


@router.put("/assignments")
def save_assignments(
    data: AssignmentsRequest,
    db: Session = Depends(get_tournament_db)
):
    tatami_ids = {
        item.id for item in db.query(KumiteTatami).all()
    }

    category_ids = {
        item.id for item in db.query(Category).all()
    }

    submitted = set()

    try:
        for item in data.assignments:
            if item.category_id in submitted:
                raise HTTPException(
                    status_code=400,
                    detail="Категория указана несколько раз"
                )

            submitted.add(item.category_id)

            if item.category_id not in category_ids:
                raise HTTPException(
                    status_code=404,
                    detail=f"Категория {item.category_id} не найдена"
                )

            if (
                item.tatami_id is not None
                and item.tatami_id not in tatami_ids
            ):
                raise HTTPException(
                    status_code=404,
                    detail=f"Татами {item.tatami_id} не найдено"
                )

            assignment = db.query(KumiteTatami).filter(
                CategoryTatami.category_id == item.category_id
            ).first()

            if item.tatami_id is None:
                if assignment:
                    db.delete(assignment)
            elif assignment:
                assignment.tatami_id = item.tatami_id
            else:
                db.add(
                    CategoryTatami(
                        category_id=item.category_id,
                        kumite_tatami_id=item.tatami_id
                    )
                )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return {"success": True}


# =========================================================
# COMPETITION SCHEDULE
# =========================================================

@router.get("/schedule")
def get_schedule(db: Session = Depends(get_tournament_db)):
    tatamis = (
        db.query(KumiteTatami)
        .order_by(KumiteTatami.number)
        .all()
    )

    categories = (
        db.query(Category)
        .order_by(Category.name)
        .all()
    )

    assignments = db.query(CategoryTatami).all()

    assignment_map = {
        item.category_id: item.kumite_tatami_id
        for item in assignments
    }

    schedule = {
        tatami.id: []
        for tatami in tatamis
    }

    medal_bouts = []

    for category in categories:
        tatami_id = assignment_map.get(category.id)

        if tatami_id is None or tatami_id not in schedule:
            continue

        matches = category_matches(db, category.id)

        if not matches:
            continue

        max_round = max(
            match.round_number for match in matches
        )

        # Предварительные бои.
        for match in matches:
            if match.round_number == max_round:
                continue

            bout = build_bout(
                category,
                match,
                max_round
            )

            bout["tatami_id"] = tatami_id
            schedule[tatami_id].append(bout)

        # Полуфиналы и бой за третье место.
        semifinal_round = max_round - 1

        semifinals = [
            match for match in matches
            if match.round_number == semifinal_round
        ]

        if max_round >= 2 and len(semifinals) >= 2:
            loser1 = get_loser(semifinals[0])
            loser2 = get_loser(semifinals[1])

            bronze = db.query(BronzeMatchResult).filter(
                BronzeMatchResult.category_id == category.id
            ).first()

            if not bronze:
                bronze = BronzeMatchResult(
                    category_id=category.id,
                    athlete1_id=loser1,
                    athlete2_id=loser2,
                    status="pending"
                )
                db.add(bronze)
                db.flush()
            elif (
                bronze.athlete1_id != loser1
                or bronze.athlete2_id != loser2
            ):
                bronze.athlete1_id = loser1
                bronze.athlete2_id = loser2
                bronze.winner_athlete_id = None
                bronze.status = "pending"

            medal_bouts.append({
                "tatami_id": tatami_id,
                "category_id": category.id,
                "category_name": category.name,
                "match_id": None,
                "bronze_match_id": bronze.id,
                "match_number": 0,
                "round_number": semifinal_round + 1,
                "bout_type": "bronze",
                "stage": "За 3-е место",
                "phase_order": -1,
                "athlete1_id": loser1,
                "athlete2_id": loser2,
                "athlete1": athlete_name(bronze.athlete1),
                "athlete2": athlete_name(bronze.athlete2),
                "winner_athlete_id": bronze.winner_athlete_id,
                "status": bronze.status
            })

        # Финал.
        finals = [
            match for match in matches
            if match.round_number == max_round
        ]

        for match in finals:
            bout = build_bout(
                category,
                match,
                max_round
            )

            bout["tatami_id"] = tatami_id
            bout["bout_type"] = "final"
            bout["stage"] = "Финал"
            bout["phase_order"] = -1

            medal_bouts.append(bout)

    result = []

    for tatami in tatamis:
        regular = schedule[tatami.id]

        regular.sort(
            key=lambda bout: (
                -bout["phase_order"],
                bout["category_name"],
                bout["match_number"]
            )
        )

        medals = [
            bout for bout in medal_bouts
            if bout["tatami_id"] == tatami.id
        ]

        medals.sort(
            key=lambda bout: (
                bout["category_id"],
                0 if bout["bout_type"] == "bronze" else 1
            )
        )

        ordered = regular + medals

        for index, bout in enumerate(ordered, start=1):
            bout["tatami_bout_number"] = index

        result.append({
            "tatami_id": tatami.id,
            "tatami_name": tatami.name,
            "bouts": ordered
        })

    db.commit()

    return result


# =========================================================
# BRONZE MATCH WINNER
# =========================================================

@router.put("/bronze/{category_id}/winner")
def set_bronze_winner(
    category_id: int,
    data: BronzeWinnerRequest,
    db: Session = Depends(get_tournament_db)
):
    bronze = db.query(BronzeMatchResult).filter(
        BronzeMatchResult.category_id == category_id
    ).first()

    if not bronze:
        raise HTTPException(
            status_code=404,
            detail="Бой за 3-е место не найден"
        )

    if not bronze.athlete1_id or not bronze.athlete2_id:
        raise HTTPException(
            status_code=400,
            detail="Участники боя за 3-е место ещё не определены"
        )

    if data.winner_athlete_id not in (
        bronze.athlete1_id,
        bronze.athlete2_id
    ):
        raise HTTPException(
            status_code=400,
            detail="Указанный спортсмен не участвует в этом бою"
        )

    bronze.winner_athlete_id = data.winner_athlete_id
    bronze.status = "completed"

    finalize_category(db, category_id)

    db.commit()

    return {"success": True}


# =========================================================
# RESULTS
# =========================================================

def serialize_result(result: Result):
    athlete = result.athlete

    return {
        "id": result.id,
        "athlete_id": athlete.id,
        "first_name": athlete.first_name,
        "last_name": athlete.last_name,
        "club": (
            athlete.club.name
            if athlete.club
            else None
        ),
        "place": result.place
    }


@router.get("/results")
def get_competition_results(
    db: Session = Depends(get_tournament_db)
):
    results = (
        db.query(KumiteResult)
        .options(
            joinedload(KumiteResult.athlete).joinedload(
                Athlete.club
            ),
            joinedload(KumiteResult.category)
        )
        .order_by(
            KumiteResult.category_id,
            KumiteResult.place
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


@router.get("/results/{category_id}")
def get_category_results(
    category_id: int,
    db: Session = Depends(get_tournament_db)
):
    results = (
        db.query(KumiteResult)
        .options(
            joinedload(KumiteResult.athlete).joinedload(
                Athlete.club
            )
        )
        .filter(KumiteResult.category_id == category_id)
        .order_by(KumiteResult.place)
        .all()
    )

    return [
        serialize_result(result)
        for result in results
        if result.athlete
    ]


@router.post("/results/{category_id}/finalize")
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