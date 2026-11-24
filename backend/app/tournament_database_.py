from functools import lru_cache
from sqlalchemy import create_engine, text, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends, HTTPException

from backend.app.database_ import DATABASE_URL, get_db
from app.models import Tournament
from app.tournament_models import TournamentBase, Athlete, Category, AthleteCategory

admin_url = make_url(DATABASE_URL).set(database='postgres')

admin_emgine = create_engine(
    admin_url,
    isolation_level="AUTOCOMMIT"
)

def get_database_name(tournament_id: int) -> str:
    return f"karate_event_{tournament_id}"

def provision_tournament_database(database_name: str):
    with admin_emgine.connect() as conn:
        exists = conn.execute(
            text("""
                 SELECT 1
                 FROM pg_database
                 WHERE datname = :database_name
            """),
            {"database_name": database_name}
        ).scalar()
        
        if not exists:
            conn.exec_driver_sql(
                f'CREATE DATABASE "{database_name}"'
            )
        
    engine = get_tournament_engine(database_name)

    TournamentBase.metadata.create_all(bind=engine)

@lru_cache(maxsize=100)
def get_tournament_engine(database_name: str):
    database_url = make_url(DATABASE_URL).set(
        database=database_name
    )

    return create_engine(
        database_url,
        pool_pre_ping=True
    )

def get_tournament_db(
        tournament_id: int,
        master_db: Session = Depends(get_db)
):
    tournament = master_db.get(
        Tournament,
        tournament_id
    )

    if tournament is None:
        raise HTTPException(
            status_code=404,
            detail="Tournament not found"
        )
    
    if (
        tournament.database_status != "ready"
        or not tournament.database_name
    ):
        raise HTTPException(
            status_code=409,
            detail="Tournament database is not ready"
        )
    
    engine = get_tournament_engine(
        tournament.database_name
    )

    TournamentSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False
    )

    db = TournamentSession()

    try:
        yield db
    finally:
        db.close()