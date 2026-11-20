from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional

from app.tournament_database import get_tournament_db
from app.tournament_models import (
    Category,
    CategoryDistribution,
    CategoryTatami,
    KataCompetition,
    KataRound,
    KataRoundParticipant,
    KataScore,
    KataCompetitionResult,
    KataTatami,
)

class TatamiRequest(BaseModel):
    count: int

class CategoryTatamiItem(BaseModel):
    category_id: int
    kata_tatami_id: Optional[int] = None
    position: int

class CategoryAssignment(BaseModel):
    category_id: int
    kata_tatami_id: Optional[int] = None


class AssignmentsRequest(BaseModel):
    assignments: list[CategoryAssignment]


class CategoryTatamiUpdate(BaseModel):
    assignments: list[CategoryTatamiItem]


router = APIRouter(
    prefix="/api/tournaments/{tournament_id}/kata-competition",
    tags=["Kata Competition"]
)


# ---------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------

def get_competition_db(db: Session, category_id: int):
    competition = (
        db.query(KataCompetition)
        .filter(KataCompetition.category_id == category_id)
        .first()
    )

    if not competition:
        raise HTTPException(404, "Соревнование по ката не найдено")

    return competition


def get_round(db: Session, round_id: int):
    kata_round = db.query(KataRound).filter(
        KataRound.id == round_id
    ).first()

    if not kata_round:
        raise HTTPException(404, "Круг не найден")

    return kata_round


def get_round_participants(db: Session, round_id: int):
    return (
        db.query(KataRoundParticipant)
        .filter(KataRoundParticipant.round_id == round_id)
        .order_by(KataRoundParticipant.position)
        .all()
    )


def participant_key(participant):
    if participant.athlete_id is not None:
        return ("athlete", participant.athlete_id)

    return ("group", participant.kata_group_id)


def get_category_participants(db: Session, category_id: int):
    rows = (
        db.query(CategoryDistribution)
        .filter(CategoryDistribution.category_id == category_id)
        .all()
    )

    print(rows)
    result = []

    for row in rows:
        if row.athlete_id is not None:
            result.append({
                "athlete_id": row.athlete_id,
                "kata_group_id": None
            })

        elif row.kata_group_id is not None:
            result.append({
                "athlete_id": None,
                "kata_group_id": row.kata_group_id
            })

    return result


def create_round(
    db: Session,
    competition_id: int,
    number: int,
    participants: list,
    round_type: str = "regular",
    source_round_id: Optional[int] = None,
    advancement_limit: Optional[int] = None
):
    kata_round = KataRound(
        competition_id=competition_id,
        number=number,
        round_type=round_type,
        status="pending",
        source_round_id=source_round_id,
        advancement_limit=advancement_limit
    )

    db.add(kata_round)
    db.flush()

    for position, participant in enumerate(participants, start=1):
        db.add(KataRoundParticipant(
            round_id=kata_round.id,
            athlete_id=participant["athlete_id"],
            kata_group_id=participant["kata_group_id"],
            position=position
        ))

    db.flush()
    return kata_round


def get_round_score(db: Session, participant_id: int):
    score = (
        db.query(KataScore)
        .filter(
            KataScore.round_participant_id == participant_id
        )
        .first()
    )

    if not score or not score.is_confirmed:
        return None

    return score


def get_round_score_data(db: Session, participant_id: int):
    score = get_round_score(db, participant_id)

    if not score:
        return None

    return {
        "total": score.total_score,
        "max": score.max_score,
        "min": score.min_score
    }


def score_is_complete(db: Session, kata_round: KataRound):
    participants = get_round_participants(db, kata_round.id)

    return all(
        get_round_score(db, participant.id) is not None
        for participant in participants
    )


def get_score_values(data: dict):
    values = [
        data.get("score1"),
        data.get("score2"),
        data.get("score3"),
        data.get("score4"),
        data.get("score5")
    ]

    if any(value is None for value in values):
        raise HTTPException(
            400,
            "Необходимо ввести оценки всех пяти судей"
        )

    for value in values:
        if not 6.0 <= float(value) <= 8.0:
            raise HTTPException(
                400,
                "Оценки должны быть от 6.0 до 8.0"
            )

        if round(float(value) * 10) != float(value) * 10:
            raise HTTPException(
                400,
                "Оценки должны выставляться с шагом 0.1"
            )

    return [round(float(value), 1) for value in values]


def calculate_score(values: list):
    sorted_values = sorted(values)

    minimum = sorted_values[0]
    maximum = sorted_values[-1]

    total = round(sum(sorted_values[1:-1]), 1)

    return {
        "total": total,
        "min": minimum,
        "max": maximum
    }


def get_limits(participant_count: int):
    if participant_count <= 3:
        return {
            2: participant_count,
            3: participant_count
        }

    if participant_count == 4:
        return {
            2: 4,
            3: 3
        }

    if participant_count == 5:
        return {
            2: 4,
            3: 3
        }

    if participant_count == 6:
        return {
            2: 5,
            3: 4
        }

    if participant_count <= 8:
        return {
            2: 6,
            3: 4
        }

    if participant_count <= 16:
        return {
            2: 8,
            3: 4
        }

    return {
        2: 16,
        3: 8
    }


def get_cumulative_score(db: Session, participant_key_value, round_ids):
    total = 0.0
    maximum = None
    minimum = None

    for round_id in round_ids:
        participants = get_round_participants(db, round_id)

        participant = next(
            (
                item for item in participants
                if participant_key(item) == participant_key_value
            ),
            None
        )

        if not participant:
            continue

        score = get_round_score_data(db, participant.id)

        if not score:
            return None

        total += score["total"]

        maximum = (
            score["max"] if maximum is None
            else max(maximum, score["max"])
        )

        minimum = (
            score["min"] if minimum is None
            else min(minimum, score["min"])
        )

    return {
        "total": round(total, 1),
        "max": maximum,
        "min": minimum
    }


def get_ranking(db: Session, round_id: int):
    participants = get_round_participants(db, round_id)

    ranking = []

    for participant in participants:
        score = get_round_score_data(db, participant.id)

        if score is None:
            raise HTTPException(
                400,
                "Не все участники получили оценки"
            )

        ranking.append({
            "participant": participant,
            "total": score["total"],
            "max": score["max"],
            "min": score["min"]
        })

    ranking.sort(
        key=lambda item: (
            -item["total"],
            -item["max"],
            -item["min"]
        )
    )

    return ranking


def find_cutoff_tie(ranking: list, limit: int):
    if len(ranking) <= limit:
        return []

    boundary = ranking[limit - 1]

    tied = [
        item for item in ranking
        if (
            item["total"] == boundary["total"]
            and item["max"] == boundary["max"]
            and item["min"] == boundary["min"]
        )
    ]

    if len(tied) <= 1:
        return []

    return tied


def make_participant_data(participant):
    return {
        "athlete_id": participant.athlete_id,
        "kata_group_id": participant.kata_group_id
    }


# ---------------------------------------------------------
# Список категорий
# ---------------------------------------------------------

@router.get("/categories")
def get_categories(
    db: Session = Depends(get_tournament_db)
):
    categories = db.query(Category).all()

    result = []

    for category in categories:
        participants = get_category_participants(
            db,
            category.id
        )

        competition = (
            db.query(KataCompetition)
            .filter(KataCompetition.category_id == category.id)
            .first()
        )

        result.append({
            "category_id": category.id,
            "category_name": category.name,
            "participant_count": len(participants),
            "competition_started": competition is not None
        })

    return result


# ---------------------------------------------------------
# Создание соревнования
# ---------------------------------------------------------

@router.post("/{category_id}/start")
def start_competition(
    category_id: int,
    db: Session = Depends(get_tournament_db)
):
    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(404, "Категория не найдена")

    existing = (
        db.query(KataCompetition)
        .filter(KataCompetition.category_id == category_id)
        .first()
    )


    participants = get_category_participants(db, category_id)

    if len(participants) < 2:
        raise HTTPException(
            400,
            "Для соревнования необходимо минимум два участника"
        )
    
    competition = existing

    if not existing:
        competition = KataCompetition(
            category_id=category_id,
            status="in_progress"
        )

        db.add(competition)
        db.flush()

        create_round(
            db,
            competition.id,
            1,
            participants
        )

        db.commit()

    return {
        "success": True,
        "competition_id": competition.id,
        "participant_count": len(participants)
    }





# ---------------------------------------------------------
# Сохранение оценок
# ---------------------------------------------------------

@router.put("/rounds/{round_id}/scores/{participant_id}")
def save_scores(
    round_id: int,
    participant_id: int,
    data: dict,
    db: Session = Depends(get_tournament_db)
):
    kata_round = get_round(db, round_id)

    if kata_round.status == "completed":
        raise HTTPException(
            400,
            "Круг уже завершён"
        )

    participant = (
        db.query(KataRoundParticipant)
        .filter(
            KataRoundParticipant.id == participant_id,
            KataRoundParticipant.round_id == round_id
        )
        .first()
    )

    if not participant:
        raise HTTPException(404, "Участник круга не найден")

    values = get_score_values(data)
    calculated = calculate_score(values)

    score = (
        db.query(KataScore)
        .filter(
            KataScore.round_participant_id == participant_id
        )
        .first()
    )

    if not score:
        score = KataScore(
            round_participant_id=participant_id
        )
        db.add(score)

    score.score1 = values[0]
    score.score2 = values[1]
    score.score3 = values[2]
    score.score4 = values[3]
    score.score5 = values[4]

    score.total_score = calculated["total"]
    score.max_score = calculated["max"]
    score.min_score = calculated["min"]
    score.is_confirmed = True

    participant.total_score = calculated["total"]

    db.commit()

    return {
        "success": True,
        "scores": values,
        "total": calculated["total"],
        "max": calculated["max"],
        "min": calculated["min"]
    }


# ---------------------------------------------------------
# Завершение круга и переход дальше
# ---------------------------------------------------------

@router.post("/rounds/{round_id}/finish")
def finish_round(
    round_id: int,
    db: Session = Depends(get_tournament_db)
):
    kata_round = get_round(db, round_id)

    if kata_round.status == "completed":
        raise HTTPException(
            400,
            "Круг уже завершён"
        )

    if not score_is_complete(db, kata_round):
        raise HTTPException(
            400,
            "Сначала необходимо выставить оценки всем участникам"
        )

    competition = (
        db.query(KataCompetition)
        .filter(KataCompetition.id == kata_round.competition_id)
        .first()
    )

    regular_rounds = (
        db.query(KataRound)
        .filter(
            KataRound.competition_id == competition.id,
            KataRound.round_type == "regular"
        )
        .order_by(KataRound.number)
        .all()
    )

    participant_count = len(
        get_round_participants(db, regular_rounds[0].id)
    )

    limits = get_limits(participant_count)

    kata_round.status = "completed"

    # Для 2–3 участников все три круга обязательны.
    if participant_count <= 3:
        if kata_round.number < 3:
            previous_participants = get_round_participants(
                db,
                kata_round.id
            )

            next_round = create_round(
                db,
                competition.id,
                kata_round.number + 1,
                [
                    make_participant_data(item)
                    for item in previous_participants
                ]
            )

            db.commit()

            return {
                "success": True,
                "next_round_id": next_round.id,
                "message": "Все участники проходят в следующий круг"
            }

        save_small_category_results(db, competition, regular_rounds)
        db.commit()

        return {
            "success": True,
            "finished": True,
            "message": "Итоговые места определены"
        }

    # Для остальных категорий всего три обычных круга.
    if kata_round.number == 3:
        save_final_round_results(db, competition, kata_round)
        db.commit()

        return {
            "success": True,
            "finished": True,
            "message": "Итоговые места определены"
        }

    # В третьем круге для категории из 4 участников
    # учитываем оценки первого и второго кругов.
    if participant_count == 4 and kata_round.number == 2:
        first_two_rounds = regular_rounds[:2]
        ranking = get_cumulative_ranking(
            db,
            first_two_rounds
        )
        limit = 3

    else:
        ranking = get_ranking(db, kata_round.id)
        limit = limits.get(kata_round.number + 1)

    if limit is None:
        db.commit()
        return {
            "success": True,
            "finished": True
        }

    tied = find_cutoff_tie(ranking, limit)

    if tied:
        tied_participants = [
            make_participant_data(item["participant"])
            for item in tied
        ]

        tie_round = create_round(
            db,
            competition.id,
            100 + kata_round.number,
            tied_participants,
            round_type="tiebreak",
            source_round_id=kata_round.id,
            advancement_limit=limit
        )

        db.commit()

        return {
            "success": True,
            "tie_required": True,
            "tie_round_id": tie_round.id,
            "tied_participants": [
                {
                    "athlete_id": item["participant"].athlete_id,
                    "kata_group_id": item["participant"].kata_group_id
                }
                for item in tied
            ],
            "message": "Необходимо провести дополнительный раунд"
        }

    selected = ranking[:limit]

    next_round = create_round(
        db,
        competition.id,
        kata_round.number + 1,
        [
            make_participant_data(item["participant"])
            for item in selected
        ]
    )

    db.commit()

    return {
        "success": True,
        "next_round_id": next_round.id,
        "advanced": len(selected)
    }


def get_cumulative_ranking(db: Session, rounds: list):
    if not rounds:
        return []

    participants = get_round_participants(db, rounds[0].id)
    ranking = []

    for participant in participants:
        score = get_cumulative_score(
            db,
            participant_key(participant),
            [item.id for item in rounds]
        )

        if score is None:
            raise HTTPException(
                400,
                "Не все оценки предыдущих кругов сохранены"
            )

        ranking.append({
            "participant": participant,
            "total": score["total"],
            "max": score["max"],
            "min": score["min"]
        })

    ranking.sort(
        key=lambda item: (
            -item["total"],
            -item["max"],
            -item["min"]
        )
    )

    return ranking


def save_final_round_results(
    db: Session,
    competition: KataCompetition,
    kata_round: KataRound
):
    ranking = get_ranking(db, kata_round.id)

    db.query(KataCompetitionResult).filter(
        KataCompetitionResult.competition_id == competition.id
    ).delete(synchronize_session=False)

    for place, item in enumerate(ranking, start=1):
        participant = item["participant"]

        db.add(KataCompetitionResult(
            competition_id=competition.id,
            athlete_id=participant.athlete_id,
            kata_group_id=participant.kata_group_id,
            place=place
        ))

    competition.status = "completed"


def save_small_category_results(
    db: Session,
    competition: KataCompetition,
    rounds: list
):
    ranking = get_cumulative_ranking(db, rounds)

    db.query(KataCompetitionResult).filter(
        KataCompetitionResult.competition_id == competition.id
    ).delete(synchronize_session=False)

    for place, item in enumerate(ranking, start=1):
        participant = item["participant"]

        db.add(KataCompetitionResult(
            competition_id=competition.id,
            athlete_id=participant.athlete_id,
            kata_group_id=participant.kata_group_id,
            place=place
        ))

    competition.status = "completed"


# ---------------------------------------------------------
# Завершение дополнительного раунда
# ---------------------------------------------------------

@router.post("/rounds/{round_id}/finish-tiebreak")
def finish_tiebreak(
    round_id: int,
    db: Session = Depends(get_tournament_db)
):
    tie_round = get_round(db, round_id)

    if tie_round.round_type != "tiebreak":
        raise HTTPException(
            400,
            "Это не дополнительный раунд"
        )

    if not score_is_complete(db, tie_round):
        raise HTTPException(
            400,
            "Необходимо выставить оценки всем участникам"
        )

    source_round = get_round(db, tie_round.source_round_id)

    if source_round.status != "completed":
        raise HTTPException(
            400,
            "Основной круг ещё не завершён"
        )

    ranking = get_ranking(db, tie_round.id)

    limit = tie_round.advancement_limit

    source_ranking = get_ranking(db, source_round.id)

    already_selected = [
        item for item in source_ranking
        if item["participant"].id not in {
            tied["participant"].id
            for tied in find_cutoff_tie(source_ranking, limit)
        }
    ]

    # Участники выше границы проходят автоматически.
    tied = find_cutoff_tie(source_ranking, limit)

    tied_keys = {
        participant_key(item["participant"])
        for item in tied
    }

    fixed = [
        item for item in source_ranking
        if participant_key(item["participant"]) not in tied_keys
        and source_ranking.index(item) < limit
    ]

    needed = limit - len(fixed)

    selected_tie = ranking[:needed]

    selected = fixed + selected_tie

    next_round_number = source_round.number + 1

    next_round = create_round(
        db,
        tie_round.competition_id,
        next_round_number,
        [
            make_participant_data(item["participant"])
            for item in selected
        ]
    )

    tie_round.status = "completed"

    db.commit()

    return {
        "success": True,
        "next_round_id": next_round.id,
        "advanced": len(selected)
    }





@router.get("/tatamis")
def get_kata_tatamis(
    db: Session = Depends(get_tournament_db),
):
    tatamis = (
        db.query(KataTatami)
        .order_by(KataTatami.number)
        .all()
    )

    return [
        {
            "id": tatami.id,
            "number": tatami.number,
            "name": tatami.name,
        }
        for tatami in tatamis
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
        db.query(KataTatami)
        .order_by(KataTatami.number)
        .all()
    )

    for tatami in existing:
        if tatami.number > data.count:
            used = db.query(KataTatami).filter(
                KataTatami.tatami_id == tatami.id
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
        for item in db.query(KataTatami).all()
    }

    for number in range(1, data.count + 1):
        if number not in existing_numbers:
            db.add(
                KataTatami(
                    name=f"Татами {number}",
                    number=number
                )
            )

    db.commit()

    return get_kata_tatamis(db)


# =========================================================
# CATEGORY ASSIGNMENTS
# =========================================================

@router.get("/assignments")
def get_kata_assignments(
    db: Session = Depends(get_tournament_db)
):
    rows = (
        db.query(CategoryTatami)
        .order_by(
            CategoryTatami.kata_tatami_id,
            CategoryTatami.position
        )
        .all()
    )

    return [
        {
            "category_id": row.category_id,
            "kata_tatami_id": row.kata_tatami_id,
            "position": row.position
        }
        for row in rows
    ]


@router.put("/assignments")
def save_kata_assignments(
    data: list[CategoryTatamiItem],
    db: Session = Depends(get_tournament_db)
):
    tatami_ids = {
        row.id for row in db.query(KataTatami).all()
    }
    category_ids = [item.category_id for item in data]

    print(data)
    if len(category_ids) != len(set(category_ids)):
        raise HTTPException(
            status_code=400,
            detail="Категория не может быть назначена дважды"
        )

    for item in data:
        if item.kata_tatami_id not in tatami_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Татами {item.kata_tatami_id} не существует"
            )

    try:
        db.query(CategoryTatami).delete(
            synchronize_session=False
        )

        for item in data:
            db.add(CategoryTatami(
                category_id=item.category_id,
                kata_tatami_id=item.kata_tatami_id,
                position=item.position
            ))

        db.commit()

        return {"success": True}

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Не удалось сохранить распределение категорий"
        )

# ---------------------------------------------------------
# Итоговые места
# ---------------------------------------------------------

@router.get("/{category_id}/results")
def get_results(
    category_id: int,
    db: Session = Depends(get_tournament_db)
):
    competition = get_competition_db(db, category_id)

    results = (
        db.query(KataCompetitionResult)
        .filter(
            KataCompetitionResult.competition_id == competition.id
        )
        .order_by(KataCompetitionResult.place)
        .all()
    )

    return [
        {
            "place": item.place,
            "athlete_id": item.athlete_id,
            "kata_group_id": item.kata_group_id
        }
        for item in results
    ]

# ---------------------------------------------------------
# Получение сетки категории
# ---------------------------------------------------------

@router.get("/{category_id}")
def get_competition(
    category_id: int,
    db: Session = Depends(get_tournament_db)
):
    competition = get_competition_by_category(db, category_id)

    rounds = (
        db.query(KataRound)
        .filter(KataRound.competition_id == competition.id)
        .order_by(KataRound.number)
        .all()
    )

    result_rounds = []

    for kata_round in rounds:
        participants = get_round_participants(
            db,
            kata_round.id
        )

        result_participants = []

        for participant in participants:
            score = (
                db.query(KataScore)
                .filter(
                    KataScore.round_participant_id == participant.id
                )
                .first()
            )

            result_participants.append({
                "id": participant.id,
                "athlete_id": participant.athlete_id,
                "kata_group_id": participant.kata_group_id,
                "position": participant.position,
                "score": {
                    "score1": score.score1,
                    "score2": score.score2,
                    "score3": score.score3,
                    "score4": score.score4,
                    "score5": score.score5,
                    "total": score.total_score,
                    "max": score.max_score,
                    "min": score.min_score,
                    "is_confirmed": score.is_confirmed
                } if score else None
            })

        result_rounds.append({
            "id": kata_round.id,
            "number": kata_round.number,
            "round_type": kata_round.round_type,
            "status": kata_round.status,
            "participants": result_participants
        })

    return {
        "competition_id": competition.id,
        "category_id": category_id,
        "status": competition.status,
        "rounds": result_rounds
    }


def get_competition_by_category(db: Session, category_id: int):
    return get_competition_db(db, category_id)