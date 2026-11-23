from random import shuffle
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
    KataGroup,
    KataGroupAthlete,
)


router = APIRouter(
    prefix="/api/tournaments/{tournament_id}/draw/kata",
    tags=["Kata Draw"]
)


class DrawItem(BaseModel):
    athlete_id: Optional[int] = None
    kata_group_id: Optional[int] = None
    position: int


class DrawSaveRequest(BaseModel):
    items: list[DrawItem]


def serialize_model(obj):
    return {
        column.name: getattr(obj, column.name)
        for column in obj.__table__.columns
    }


def get_club_data(db: Session, athlete: Athlete):
    if athlete.club_id:
        club = db.query(Club).filter(
            Club.id == athlete.club_id
        ).first()

        if club:
            return {
                "club_id": club.id,
                "club_name": club.name
            }

    if athlete.club:
        return {
            "club_id": None,
            "club_name": athlete.club
        }

    return {
        "club_id": None,
        "club_name": "Без клуба"
    }


def get_participants(db: Session, category_id: int):
    distributions = (
        db.query(CategoryDistribution)
        .filter(
            CategoryDistribution.category_id == category_id
        )
        .all()
    )

    participants = []

    for item in distributions:
        if item.athlete_id is not None:
            athlete = db.query(Athlete).filter(
                Athlete.id == item.athlete_id
            ).first()

            if not athlete:
                continue

            club = get_club_data(db, athlete)

            participants.append({
                "key": f"athlete_{athlete.id}",
                "athlete_id": athlete.id,
                "kata_group_id": None,
                "name": " ".join(
                    str(value)
                    for value in [
                        athlete.last_name,
                        athlete.first_name,
                        athlete.second_name
                    ]
                    if value
                ),
                "clubs": [club],
                "position": item.draw_order,
                "distribution_id": item.id
            })

        elif item.kata_group_id is not None:
            group = db.query(KataGroup).filter(
                KataGroup.id == item.kata_group_id
            ).first()

            if not group:
                continue

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

            clubs = []
            seen_clubs = set()

            for athlete in members:
                club = get_club_data(db, athlete)

                club_key = (
                    club["club_id"]
                    if club["club_id"] is not None
                    else club["club_name"]
                )

                if club_key not in seen_clubs:
                    seen_clubs.add(club_key)
                    clubs.append(club)

            participants.append({
                "key": f"group_{group.id}",
                "athlete_id": None,
                "kata_group_id": group.id,
                "name": group.name,
                "clubs": clubs,
                "athletes": [
                    {
                        "id": athlete.id,
                        "name": " ".join(
                            str(value)
                            for value in [
                                athlete.last_name,
                                athlete.first_name,
                                athlete.second_name
                            ]
                            if value
                        )
                    }
                    for athlete in members
                ],
                "position": item.draw_order,
                "distribution_id": item.id
            })

    return participants


def participant_club_keys(participant):
    keys = set()

    for club in participant["clubs"]:
        key = (
            club["club_id"]
            if club["club_id"] is not None
            else club["club_name"]
        )

        if key and key != "Без клуба":
            keys.add(str(key))

    return keys


def generate_draw_order(participants):
    """
    Жадный алгоритм: выбирает следующего участника так,
    чтобы минимизировать близость участников одного клуба.
    """

    remaining = participants.copy()
    shuffle(remaining)

    result = []

    while remaining:
        best_participant = None
        best_score = None

        for candidate in remaining:
            candidate_clubs = participant_club_keys(candidate)

            score = 0

            for position, placed in enumerate(result):
                common_clubs = (
                    candidate_clubs
                    & participant_club_keys(placed)
                )

                if common_clubs:
                    distance = len(result) - position
                    score += len(common_clubs) / distance

            if best_score is None or score < best_score:
                best_score = score
                best_participant = candidate

        result.append(best_participant)
        remaining.remove(best_participant)

    return result


@router.get("/{category_id}")
def get_kata_draw(
    tournament_id: int,
    category_id: int,
    db: Session = Depends(get_tournament_db)
):
    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Категория не найдена"
        )

    participants = get_participants(db, category_id)

    participants.sort(
        key=lambda item: (
            item["position"] is None,
            item["position"] or 0
        )
    )

    return {
        "category": serialize_model(category),
        "participants": participants,
        "count": len(participants),
        "is_drawn": all(
            item["position"] is not None
            for item in participants
        )
    }


@router.post("/{category_id}/generate")
def generate_kata_draw(
    tournament_id: int,
    category_id: int,
    db: Session = Depends(get_tournament_db)
):
    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Категория не найдена"
        )

    participants = get_participants(db, category_id)

    if not participants:
        raise HTTPException(
            status_code=400,
            detail="В категории нет участников"
        )

    ordered = generate_draw_order(participants)

    for position, participant in enumerate(ordered, start=1):
        distribution = db.query(CategoryDistribution).filter(
            CategoryDistribution.id == participant["distribution_id"]
        ).first()

        distribution.draw_order = position

    db.commit()

    return {
        "message": "Жеребьёвка сформирована",
        "count": len(ordered),
        "participants": get_participants(db, category_id)
    }


@router.put("/{category_id}")
def save_kata_draw(
    tournament_id: int,
    category_id: int,
    data: DrawSaveRequest,
    db: Session = Depends(get_tournament_db)
):
    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Категория не найдена"
        )

    distributions = (
        db.query(CategoryDistribution)
        .filter(
            CategoryDistribution.category_id == category_id
        )
        .all()
    )

    distribution_map = {
        (
            item.athlete_id,
            item.kata_group_id
        ): item
        for item in distributions
    }

    submitted_keys = set()

    for item in data.items:
        if (item.athlete_id is None) == (item.kata_group_id is None):
            raise HTTPException(
                status_code=400,
                detail="Для участника нужно указать athlete_id или kata_group_id"
            )

        key = (item.athlete_id, item.kata_group_id)

        if key in submitted_keys:
            raise HTTPException(
                status_code=400,
                detail="Участник указан несколько раз"
            )

        submitted_keys.add(key)

        if key not in distribution_map:
            raise HTTPException(
                status_code=400,
                detail="Участник не найден в этой категории"
            )

        if item.position < 1:
            raise HTTPException(
                status_code=400,
                detail="Позиция должна начинаться с 1"
            )

    if len(submitted_keys) != len(distributions):
        raise HTTPException(
            status_code=400,
            detail="Передан не весь список участников категории"
        )

    positions = [item.position for item in data.items]

    if len(set(positions)) != len(positions):
        raise HTTPException(
            status_code=400,
            detail="Позиции не должны повторяться"
        )

    if set(positions) != set(range(1, len(distributions) + 1)):
        raise HTTPException(
            status_code=400,
            detail="Позиции должны идти подряд начиная с 1"
        )

    for item in data.items:
        key = (item.athlete_id, item.kata_group_id)
        distribution_map[key].draw_order = item.position

    db.commit()

    return {
        "message": "Порядок жеребьёвки сохранён",
        "count": len(data.items)
    }