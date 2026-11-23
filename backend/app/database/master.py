from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import DATABASE_URL

master_engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

MasterSession = sessionmaker(
    bind=master_engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = MasterSession()
    try:
        yield db
    finally:
        db.close()