from sqlmodel import SQLModel

from app.db import models as _models  # noqa: F401  (registers tables on SQLModel.metadata)
from app.db.session import engine


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    init_db()
