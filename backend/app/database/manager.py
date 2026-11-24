# app/database/manager.py

from threading import Lock

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DATABASE_URL


# ============================================================
# Tournament Database Manager
# ============================================================

class TournamentDatabaseManager:

    def __init__(self) -> None:
        self._engines: dict[str, Engine] = {}
        self._session_factories: dict[
            str, sessionmaker[Session]
        ] = {}

        self._lock = Lock()

    # --------------------------------------------------------
    # Engine
    # --------------------------------------------------------

    def get_engine(self, database_name: str) -> Engine:

        with self._lock:

            engine = self._engines.get(database_name)

            if engine is None:

                database_url = make_url(DATABASE_URL).set(
                    database=database_name
                )

                engine = create_engine(
                    database_url,
                    pool_pre_ping=True,
                )

                self._engines[database_name] = engine

            return engine

    # --------------------------------------------------------
    # Session Factory
    # --------------------------------------------------------

    def get_session_factory(
        self,
        database_name: str,
    ) -> sessionmaker[Session]:

        with self._lock:

            factory = self._session_factories.get(
                database_name
            )

            if factory is None:

                engine = self.get_engine(database_name)

                factory = sessionmaker(
                    bind=engine,
                    autoflush=False,
                    expire_on_commit=False,
                )

                self._session_factories[
                    database_name
                ] = factory

            return factory

    # --------------------------------------------------------
    # Create Session
    # --------------------------------------------------------

    def create_session(
        self,
        database_name: str,
    ) -> Session:

        factory = self.get_session_factory(
            database_name
        )

        return factory()

    # --------------------------------------------------------
    # Dispose Database Engine
    # --------------------------------------------------------

    def dispose(self, database_name: str) -> None:

        with self._lock:

            engine = self._engines.pop(
                database_name,
                None,
            )

            self._session_factories.pop(
                database_name,
                None,
            )

            if engine is not None:
                engine.dispose()

    # --------------------------------------------------------
    # Dispose All
    # --------------------------------------------------------

    def dispose_all(self) -> None:

        with self._lock:

            engines = list(
                self._engines.values()
            )

            self._engines.clear()
            self._session_factories.clear()

            for engine in engines:
                engine.dispose()


# ============================================================
# Singleton Manager
# ============================================================

tournament_db_manager = TournamentDatabaseManager()