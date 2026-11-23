
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database.master import get_db
from app.database.tournament import get_tournament_db
from app.database.provisioner import (
    get_database_name,
    provision_tournament_database,
    drop_tournament_database,
)

from app.models import Tournament
from app.schemas import TournamentCreate, TournamentResponse
from app.tournament_models import Athlete


router = APIRouter(
    prefix="/api/tournaments",
    tags=["Tournaments"],
)


# --------------------------------------------------
# GET: Получить список турниров
# --------------------------------------------------

@router.get("/", response_model=list[TournamentResponse])
def get_tournaments(db: Session = Depends(get_db)):
    query = select(Tournament).order_by(Tournament.id.desc())
    return db.scalars(query).all()


# --------------------------------------------------
# GET: Получить один турнир
# --------------------------------------------------

@router.get("/{tournament_id}", response_model=TournamentResponse)
def get_tournament(
    tournament_id: int,
    db: Session = Depends(get_db),
):
    tournament = db.get(Tournament, tournament_id)

    if tournament is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found",
        )

    return tournament


# --------------------------------------------------
# POST: Создать турнир и отдельную базу данных
# --------------------------------------------------

@router.post(
    "/",
    response_model=TournamentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_tournament(
    data: TournamentCreate,
    db: Session = Depends(get_db),
):
    tournament = Tournament(
        **data.model_dump(),
        database_status="provisioning",
    )

    db.add(tournament)
    db.commit()
    db.refresh(tournament)

    tournament_id = tournament.id
    database_name = get_database_name(tournament_id)

    try:
        tournament.database_name = database_name
        db.commit()

        # Создаём отдельную базу и таблицы турнира
        provision_tournament_database(database_name)

        # Отмечаем успешное создание
        tournament.database_status = "ready"
        db.commit()
        db.refresh(tournament)

        return tournament

    except Exception as e:
        db.rollback()

        # Сохраняем статус ошибки в главной БД
        failed_tournament = db.get(Tournament, tournament_id)

        if failed_tournament is not None:
            failed_tournament.database_name = database_name
            failed_tournament.database_status = "failed"
            db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tournament database: {str(e)}",
        ) from e


# --------------------------------------------------
# PUT: Обновить данные турнира
# --------------------------------------------------

@router.put(
    "/{tournament_id}",
    response_model=TournamentResponse,
)
def update_tournament(
    tournament_id: int,
    data: TournamentCreate,
    db: Session = Depends(get_db),
):
    tournament = db.get(Tournament, tournament_id)

    if tournament is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found",
        )

    for key, value in data.model_dump().items():
        setattr(tournament, key, value)

    db.commit()
    db.refresh(tournament)

    return tournament


# --------------------------------------------------
# DELETE: Удалить турнир и его базу данных
# --------------------------------------------------

@router.delete(
    "/{tournament_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_tournament(
    tournament_id: int,
    db: Session = Depends(get_db),
):
    tournament = db.get(Tournament, tournament_id)

    if tournament is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found",
        )

    database_name = tournament.database_name

    try:
        # Сначала удаляем отдельную базу турнира
        if database_name:
            drop_tournament_database(database_name)

        # Затем удаляем запись из главной БД
        db.delete(tournament)
        db.commit()

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tournament: {str(e)}",
        ) from e


# --------------------------------------------------
# GET: Проверить подключение к базе турнира
# --------------------------------------------------

@router.get("/{tournament_id}/database-check")
def check_tournament_database(
    tournament_id: int,
    db: Session = Depends(get_tournament_db),
):
    athletes_count = db.scalar(
        select(func.count()).select_from(Athlete)
    )

    return {
        "tournament_id": tournament_id,
        "connection": "successful",
        "athletes_count": athletes_count or 0,
    }
