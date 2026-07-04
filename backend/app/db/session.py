from collections.abc import Generator

from sqlalchemy import event
from sqlmodel import Session, create_engine

from app.core.config import get_settings

settings = get_settings()


def is_sqlite_url(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def create_configured_engine(database_url: str):
    connect_args = {"check_same_thread": False} if is_sqlite_url(database_url) else {}
    configured_engine = create_engine(database_url, echo=False, connect_args=connect_args)

    if is_sqlite_url(database_url):

        @event.listens_for(configured_engine, "connect")
        def set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
            finally:
                cursor.close()

    return configured_engine


engine = create_configured_engine(settings.database_url)


def new_session() -> Session:
    return Session(engine)


def get_session() -> Generator[Session, None, None]:
    with new_session() as session:
        yield session
