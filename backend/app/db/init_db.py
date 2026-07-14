from sqlalchemy import Engine
from sqlmodel import SQLModel

from app.db import models as _models  # noqa: F401  (registers tables on SQLModel.metadata)
from app.db.migrations import run_sqlite_migrations
from app.db.session import engine


def init_db(database_engine: Engine | None = None) -> None:
    active_engine = database_engine or engine
    SQLModel.metadata.create_all(active_engine)
    run_sqlite_migrations(active_engine)


if __name__ == "__main__":
    init_db()
