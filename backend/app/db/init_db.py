from sqlmodel import SQLModel

from app.db import models as _models  # noqa: F401  (registers tables on SQLModel.metadata)
from app.db.migrations import migrate_sqlite_schema
from app.db.session import engine


def init_db(db_engine=engine) -> None:
    SQLModel.metadata.create_all(db_engine)
    migrate_sqlite_schema(db_engine)


if __name__ == "__main__":
    init_db()
