import math
import random
import re

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.tournament_database_ import get_tournament_db
from app.tournament_models import (
    Category,
    CategoryDistribution,
    Athlete,
    Club,
    KumiteDrawEntry,
    KumiteDrawMatch,
)
from app.routers.kumite_competition import finalize_category


router = APIRouter(
    prefix="/api/tournaments/{tournament_id}/draw/kumite",
    tags=["Kumite draw"]
)


# ============================================================
# СХЕМЫ ЗАПРОСОВ
# ============================================================

class DrawSlot(BaseModel):
    position: int
    athlete_id: Optional[int] = None


class DrawSlotsRequest(BaseModel):
    slots: list[DrawSlot]


class DrawItem(BaseModel):
    athlete_id: int
    position: int


class DrawSaveRequest(BaseModel):
    items: list[DrawItem]


class WinnerRequest(BaseModel):
    winner_athlete_id: Optional[int] = None


# ============================================================
# ОБЩИЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def serialize_model(obj):
    if obj is None:
        return None

    return {
        column.name: getattr(obj, column.name)
        for column in obj.__table__.columns
    }


def get_category_or_404(db, category_id):
    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(404, "Категория не найдена")

    return category


def athlete_name(athlete):
    return " ".join(
        str(value).strip()
        for value in [
            athlete.last_name,
            athlete.first_name,
            athlete.second_name
        ]
        if value
    )


def get_club_data(db, athlete):
    if athlete.club_id:
        club = db.query(Club).filter(
            Club.id == athlete.club_id
        ).first()

        if club:
            return club.id, club.name

    return None, getattr(athlete, "club", None)


def get_athlete_map(db, participants):
    ids = [item["athlete_id"] for item in participants]

    athletes = db.query(Athlete).filter(
        Athlete.id.in_(ids)
    ).all() if ids else []

    return {
        athlete.id: athlete_name(athlete)
        for athlete in athletes
    }


# ============================================================
# ПОДГОТОВКА УЧАСТНИКОВ К ЖЕРЕБЬЁВКЕ
# ============================================================

def normalize_rank(value):
    value = str(value or "").lower().strip()
    value = value.replace("ё", "е")
    value = re.sub(r"[.\-–—]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value


def get_rank_priority(rank):
    value = normalize_rank(rank)

    if "змс" in value or "заслуженный мастер спорта" in value:
        return 1

    if "мсмк" in value or "международного класса" in value:
        return 2

    if value == "мс" or "мастер спорта" in value:
        return 3

    if value == "кмс" or "кандидат в мастера" in value:
        return 4

    if value in (
        "i", "1", "1 разряд", "i разряд",
        "1 спортивный разряд"
    ):
        return 5

    if value in (
        "ii", "2", "2 разряд", "ii разряд",
        "2 спортивный разряд"
    ):
        return 6

    if value in (
        "iii", "3", "3 разряд", "iii разряд",
        "3 спортивный разряд"
    ):
        return 7

    if "1" in value and "разряд" in value:
        return 5

    if "2" in value and "разряд" in value:
        return 6

    if "3" in value and "разряд" in value:
        return 7

    return 8


def get_participants(db, category_id):
    distributions = db.query(CategoryDistribution).filter(
        CategoryDistribution.category_id == category_id,
        CategoryDistribution.athlete_id.isnot(None)
    ).all()

    result = []

    for item in distributions:
        athlete = db.query(Athlete).filter(
            Athlete.id == item.athlete_id
        ).first()

        if not athlete:
            continue

        club_id, club_name = get_club_data(db, athlete)

        coach_id = getattr(athlete, "coach_id", None)

        result.append({
            "athlete_id": athlete.id,
            "name": athlete_name(athlete),
            "club_id": club_id,
            "club_name": club_name,
            "coach_id": coach_id,
            "coach_name": f"ID {coach_id}" if coach_id else None,
            "rank_sport": getattr(athlete, "rank_sport", None),
            "rank_priority": get_rank_priority(
                getattr(athlete, "rank_sport", None)
            )
        })

    return result


# ============================================================
# АЛГОРИТМ ЖЕРЕБЬЁВКИ
# ============================================================

def get_bracket_size(count):
    if count <= 0:
        return 0

    return 1 << (count - 1).bit_length()


def get_seed_positions(size):
    positions = [1, 2]

    while len(positions) < size:
        next_seed = len(positions) * 2 + 1

        positions = [
            value
            for seed in positions
            for value in (seed, next_seed - seed)
        ]

    return positions


def conflict_score(first, second):
    score = 0

    same_club = (
        first.get("club_id")
        and first.get("club_id") == second.get("club_id")
    ) or (
        first.get("club_name")
        and first.get("club_name") == second.get("club_name")
    )

    if same_club:
        score += 100

    if (
        first.get("coach_id")
        and first.get("coach_id") == second.get("coach_id")
    ):
        score += 60

    return score


def evaluate_seed_order(participants):
    count = len(participants)
    size = get_bracket_size(count)
    positions = get_seed_positions(size)

    score = 0

    for index in range(0, size, 2):
        seed1 = positions[index]
        seed2 = positions[index + 1]

        if seed1 > count or seed2 > count:
            continue

        score += conflict_score(
            participants[seed1 - 1],
            participants[seed2 - 1]
        )

    return score


def generate_optimized_order(participants):
    participants = sorted(
        participants,
        key=lambda item: item["rank_priority"]
    )

    if len(participants) < 2:
        return participants

    best_order = list(participants)
    best_score = evaluate_seed_order(best_order)

    iterations = min(
        5000,
        max(500, len(participants) * 200)
    )

    for _ in range(iterations):
        candidate = list(participants)

        groups = {}

        for index, athlete in enumerate(candidate):
            groups.setdefault(
                athlete["rank_priority"], []
            ).append(index)

        for indexes in groups.values():
            values = [candidate[index] for index in indexes]
            random.shuffle(values)

            for index, athlete in zip(indexes, values):
                candidate[index] = athlete

        score = evaluate_seed_order(candidate)

        if score < best_score:
            best_score = score
            best_order = candidate

        if best_score == 0:
            break

    return best_order


# ============================================================
# СОХРАНЕНИЕ И ЧТЕНИЕ ПОРЯДКА УЧАСТНИКОВ
# ============================================================

def save_order(db, category_id, participants):
    db.query(KumiteDrawEntry).filter(
        KumiteDrawEntry.category_id == category_id
    ).delete(synchronize_session=False)

    for position, athlete in enumerate(participants, start=1):
        db.add(KumiteDrawEntry(
            category_id=category_id,
            athlete_id=athlete["athlete_id"],
            draw_position=position
        ))

    db.flush()


def get_saved_order(db, category_id, participants):
    saved = db.query(KumiteDrawEntry).filter(
        KumiteDrawEntry.category_id == category_id
    ).order_by(
        KumiteDrawEntry.draw_position
    ).all()

    by_id = {
        item["athlete_id"]: item
        for item in participants
    }

    ordered = [
        by_id[item.athlete_id]
        for item in saved
        if item.athlete_id in by_id
    ]

    saved_ids = {
        item["athlete_id"]
        for item in ordered
    }

    ordered.extend(
        item
        for item in participants
        if item["athlete_id"] not in saved_ids
    )

    return ordered


# ============================================================
# ПОСТРОЕНИЕ ОЛИМПИЙСКОЙ СЕТКИ
# ============================================================

def rebuild_following_rounds(
    db: Session,
    category_id: int,
    from_round: int = 1
):
    matches = db.query(KumiteDrawMatch).filter(
        KumiteDrawMatch.category_id == category_id
    ).order_by(
        KumiteDrawMatch.round_number,
        KumiteDrawMatch.match_number
    ).all()

    rounds = {}

    for match in matches:
        rounds.setdefault(
            match.round_number, []
        ).append(match)

    if from_round not in rounds:
        return

    def resolve_match(match):
        if match.status == "completed":
            return match.winner_athlete_id, True

        if match.status == "bye":
            athlete_id = (
                match.winner_athlete_id
                or match.athlete1_id
                or match.athlete2_id
            )
            return athlete_id, True

        if match.status == "empty":
            return None, True

        return None, False

    max_round = max(rounds.keys())

    for round_number in range(from_round + 1, max_round + 1):
        previous_matches = rounds.get(round_number - 1, [])
        current_matches = rounds.get(round_number, [])

        for match in current_matches:
            first_index = (match.match_number - 1) * 2
            second_index = first_index + 1

            previous_first = (
                previous_matches[first_index]
                if first_index < len(previous_matches)
                else None
            )

            previous_second = (
                previous_matches[second_index]
                if second_index < len(previous_matches)
                else None
            )

            first_id, first_ready = (
                resolve_match(previous_first)
                if previous_first
                else (None, True)
            )

            second_id, second_ready = (
                resolve_match(previous_second)
                if previous_second
                else (None, True)
            )

            match.athlete1_id = first_id
            match.athlete2_id = second_id
            match.winner_athlete_id = None

            if not first_ready or not second_ready:
                match.status = "pending"

            elif first_id is None and second_id is None:
                match.status = "empty"

            elif first_id is None or second_id is None:
                match.status = "bye"
                match.winner_athlete_id = first_id or second_id

            else:
                match.status = "pending"

    db.flush()


def create_olympic_matches_from_slots(
    db,
    category_id,
    slots
):
    slots = sorted(
        slots,
        key=lambda item: item.position
    )

    # Удаляем старую сетку.
    db.query(KumiteDrawMatch).filter(
        KumiteDrawMatch.category_id == category_id
    ).delete(synchronize_session=False)

    db.flush()

    # Создаём первый раунд.
    for index in range(0, len(slots), 2):
        first = slots[index].athlete_id
        second = slots[index + 1].athlete_id

        if first is not None and second is not None:
            status = "pending"
            winner = None

        elif first is not None or second is not None:
            status = "bye"
            winner = first or second

        else:
            status = "empty"
            winner = None

        db.add(KumiteDrawMatch(
            category_id=category_id,
            round_number=1,
            match_number=index // 2 + 1,
            athlete1_id=first,
            athlete2_id=second,
            winner_athlete_id=winner,
            status=status
        ))

    db.flush()

    # Создаём все последующие раунды.
    match_count = len(slots) // 2
    round_number = 2

    while match_count > 1:
        match_count //= 2

        for match_number in range(1, match_count + 1):
            db.add(KumiteDrawMatch(
                category_id=category_id,
                round_number=round_number,
                match_number=match_number,
                athlete1_id=None,
                athlete2_id=None,
                winner_athlete_id=None,
                status="pending"
            ))

        db.flush()
        round_number += 1

    # Переносим проходящих по BYE участников.
    rebuild_following_rounds(
        db,
        category_id,
        from_round=1
    )


def create_olympic_matches(db, category_id, participants):
    count = len(participants)
    size = get_bracket_size(count)

    if size < 4:
        return

    seed_positions = get_seed_positions(size)

    slots = []

    for position, seed in enumerate(seed_positions, start=1):
        athlete_id = (
            participants[seed - 1]["athlete_id"]
            if seed <= count
            else None
        )

        slots.append(DrawSlot(
            position=position,
            athlete_id=athlete_id
        ))

    create_olympic_matches_from_slots(
        db,
        category_id,
        slots
    )


# ============================================================
# ФОРМИРОВАНИЕ ОТВЕТА API
# ============================================================

def create_round_robin(participants):
    matches = []

    for i in range(len(participants)):
        for j in range(i + 1, len(participants)):
            matches.append({
                "match_number": len(matches) + 1,
                "athlete1": participants[i]["name"],
                "athlete2": participants[j]["name"]
            })

    return matches


def get_match_side_name(match, athlete_id, names):
    if athlete_id is not None:
        return names.get(athlete_id, f"ID {athlete_id}")

    if match.status == "bye":
        return "BYE"

    if match.status == "empty":
        return "—"

    return "Ожидает победителя"


def build_response(db, category, participants):
    count = len(participants)

    response = {
        "category": serialize_model(category),
        "participants": participants,
        "format": None,
        "matches": [],
        "rounds": []
    }

    if count < 2:
        response["format"] = "empty"
        return response

    # if count == 2:
    #     response["format"] = "final"
    #     response["matches"] = [{
    #         "athlete1": participants[0]["name"],
    #         "athlete2": participants[1]["name"]
    #     }]
    #     return response

    if count == 3:
        response["format"] = "round_robin"
        response["matches"] = create_round_robin(participants)
        return response

    response["format"] = "olympic"

    matches = db.query(KumiteDrawMatch).filter(
        KumiteDrawMatch.category_id == category.id
    ).order_by(
        KumiteDrawMatch.round_number,
        KumiteDrawMatch.match_number
    ).all()

    names = get_athlete_map(db, participants)
    rounds = {}

    for match in matches:
        rounds.setdefault(match.round_number, []).append({
            "id": match.id,
            "round_number": match.round_number,
            "match_number": match.match_number,
            "athlete1_id": match.athlete1_id,
            "athlete2_id": match.athlete2_id,
            "athlete1": get_match_side_name(
                match, match.athlete1_id, names
            ),
            "athlete2": get_match_side_name(
                match, match.athlete2_id, names
            ),
            "winner_athlete_id": match.winner_athlete_id,
            "winner": names.get(match.winner_athlete_id)
                if match.winner_athlete_id else None,
            "status": match.status
        })

    total_rounds = len(rounds)

    response["rounds"] = [
        {
            "round_number": number,
            "name": (
                "Финал" if number == total_rounds
                else "Полуфинал" if number == total_rounds - 1
                else f"Круг {number}"
            ),
            "matches": round_matches
        }
        for number, round_matches in sorted(rounds.items())
    ]

    return response

def create_two_athlete_final(
    db: Session,
    category_id: int,
    athlete_ids: list[int]
):
    if len(athlete_ids) != 2:
        raise HTTPException(
            status_code=400,
            detail="Для финала нужны ровно два спортсмена"
        )

    db.query(KumiteDrawMatch).filter(
        KumiteDrawMatch.category_id == category_id
    ).delete(synchronize_session=False)

    match = KumiteDrawMatch(
        category_id=category_id,
        round_number=1,
        match_number=1,
        athlete1_id=athlete_ids[0],
        athlete2_id=athlete_ids[1],
        winner_athlete_id=None,
        status="pending"
    )

    db.add(match)
    db.flush()

    return match

# ============================================================
# API: ПОЛУЧЕНИЕ ЖЕРЕБЬЁВКИ
# ============================================================

@router.get("/{category_id}")
def get_kumite_draw(
    tournament_id: int,
    category_id: int,
    db: Session = Depends(get_tournament_db)
):
    category = get_category_or_404(db, category_id)

    participants = get_participants(db, category_id)
    participants = get_saved_order(
        db, category_id, participants
    )

    return build_response(db, category, participants)


# ============================================================
# API: АВТОМАТИЧЕСКАЯ ГЕНЕРАЦИЯ ЖЕРЕБЬЁВКИ
# ============================================================

@router.post("/{category_id}/generate")
def generate_kumite_draw(
    tournament_id: int,
    category_id: int,
    db: Session = Depends(get_tournament_db)
):
    category = get_category_or_404(db, category_id)
    participants = get_participants(db, category_id)

    if len(participants) < 2:
        raise HTTPException(
            400,
            "Для жеребьёвки необходимо минимум два спортсмена"
        )
    if len(participants) == 2:
        athlete_ids = [p["athlete_id"] for p in participants]

        create_two_athlete_final(
            db=db,
            category_id=category_id,
            athlete_ids=athlete_ids
        )

        db.commit()

        return build_response(
            db,
            category,
            participants
        )
    elif len(participants) == 3:
        participants = list(participants)
        random.shuffle(participants)
    else:
        participants = generate_optimized_order(participants)

    save_order(db, category_id, participants)

    if len(participants) >= 4:
        create_olympic_matches(
            db, category_id, participants
        )
    else:
        db.query(KumiteDrawMatch).filter(
            KumiteDrawMatch.category_id == category_id
        ).delete(synchronize_session=False)

    db.commit()

    return build_response(db, category, participants)


# ============================================================
# API: СОХРАНЕНИЕ ПОРЯДКА СПИСКА УЧАСТНИКОВ
# Старый endpoint, если он ещё используется Angular.
# ============================================================

@router.put("/{category_id}")
def save_kumite_order(
    tournament_id: int,
    category_id: int,
    request: DrawSaveRequest,
    db: Session = Depends(get_tournament_db)
):
    category = get_category_or_404(db, category_id)

    participants = get_participants(db, category_id)
    actual_ids = {
        item["athlete_id"] for item in participants
    }

    requested_ids = [
        item.athlete_id for item in request.items
    ]

    if len(requested_ids) != len(set(requested_ids)):
        raise HTTPException(
            400,
            "В списке есть повторяющиеся спортсмены"
        )

    if set(requested_ids) != actual_ids:
        raise HTTPException(
            400,
            "Список спортсменов не совпадает с распределением категории"
        )

    positions = sorted(
        item.position for item in request.items
    )

    if positions != list(range(1, len(request.items) + 1)):
        raise HTTPException(
            400,
            "Позиции должны идти подряд, начиная с 1"
        )

    by_id = {
        item["athlete_id"]: item
        for item in participants
    }

    ordered = [
        by_id[item.athlete_id]
        for item in sorted(
            request.items,
            key=lambda x: x.position
        )
    ]

    save_order(db, category_id, ordered)

    if len(ordered) >= 4:
        create_olympic_matches(
            db, category_id, ordered
        )
    else:
        db.query(KumiteDrawMatch).filter(
            KumiteDrawMatch.category_id == category_id
        ).delete(synchronize_session=False)

    db.commit()

    return build_response(
        db,
        category,
        ordered
    )


# ============================================================
# API: СОХРАНЕНИЕ ПЕРЕТАСКИВАНИЯ В САМОЙ СЕТКЕ
# ============================================================

@router.put("/{category_id}/slots")
def save_draw_slots(
    tournament_id: int,
    category_id: int,
    data: DrawSlotsRequest,
    db: Session = Depends(get_tournament_db)
):
    get_category_or_404(db, category_id)

    entries = db.query(KumiteDrawEntry).filter(
        KumiteDrawEntry.category_id == category_id
    ).all()

    entry_by_athlete = {
        entry.athlete_id: entry
        for entry in entries
    }

    count = len(entries)

    if count < 4:
        raise HTTPException(
            400,
            "Перетаскивание доступно для олимпийской сетки от 4 участников"
        )

    expected_size = get_bracket_size(count)

    if len(data.slots) != expected_size:
        raise HTTPException(
            400,
            f"Сетка должна содержать {expected_size} позиций"
        )

    positions = [
        slot.position for slot in data.slots
    ]

    if sorted(positions) != list(range(1, expected_size + 1)):
        raise HTTPException(
            400,
            "Позиции сетки должны идти подряд, начиная с 1"
        )

    submitted_ids = [
        slot.athlete_id
        for slot in data.slots
        if slot.athlete_id is not None
    ]

    if len(submitted_ids) != len(set(submitted_ids)):
        raise HTTPException(
            400,
            "Спортсмен повторяется в сетке"
        )

    if set(submitted_ids) != set(entry_by_athlete.keys()):
        raise HTTPException(
            400,
            "Список спортсменов не совпадает с участниками категории"
        )

    # Временно меняем позиции, чтобы не нарушить UNIQUE.
    for index, entry in enumerate(entries):
        entry.draw_position = -(10_000_000 + index)

    db.flush()

    # Сохраняем новые позиции спортсменов.
    for slot in data.slots:
        if slot.athlete_id is not None:
            entry_by_athlete[
                slot.athlete_id
            ].draw_position = slot.position

    # Пересоздаём всю сетку и все последующие раунды.
    create_olympic_matches_from_slots(
        db,
        category_id,
        data.slots
    )

    db.commit()

    category = get_category_or_404(db, category_id)
    participants = get_participants(db, category_id)
    participants = get_saved_order(
        db, category_id, participants
    )

    return build_response(db, category, participants)


# ============================================================
# API: СОХРАНЕНИЕ РЕЗУЛЬТАТА БОЯ
# ============================================================

@router.put("/{category_id}/matches/{match_id}/winner")
def set_kumite_match_winner(
    tournament_id: int,
    category_id: int,
    match_id: int,
    request: WinnerRequest,
    db: Session = Depends(get_tournament_db)
):
    match = db.query(KumiteDrawMatch).filter(
        KumiteDrawMatch.id == match_id,
        KumiteDrawMatch.category_id == category_id
    ).first()

    if not match:
        raise HTTPException(404, "Бой не найден")

    winner_id = request.winner_athlete_id

    if winner_id is not None and winner_id not in (
        match.athlete1_id,
        match.athlete2_id
    ):
        raise HTTPException(
            400,
            "Победитель должен быть одним из участников этого боя"
        )

    if match.status in ("bye", "empty"):
        if winner_id is not None:
            raise HTTPException(
                400,
                "В этом бою нельзя выбрать победителя вручную"
            )

        # BYE и пустой бой не превращаем в completed.
        return build_response(
            db,
            get_category_or_404(db, category_id),
            get_saved_order(
                db,
                category_id,
                get_participants(db, category_id)
            )
        )

    match.winner_athlete_id = winner_id
    match.status = "completed" if winner_id else "pending"

    finalize_category(db, category_id)
    db.commit()

    db.flush()

    # Пересчитываем раунды, следующие за изменённым боем.
    rebuild_following_rounds(
        db,
        category_id,
        from_round=match.round_number
    )

    db.commit()

    category = get_category_or_404(db, category_id)
    participants = get_participants(db, category_id)
    participants = get_saved_order(
        db, category_id, participants
    )

    return build_response(db, category, participants)