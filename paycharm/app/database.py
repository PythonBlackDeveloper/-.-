# paycharm/app/database.py

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from paycharm.app.config import settings


# Создаём engine для подключения к PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,  # теперь это обычная строка из .env
    future=True,
    echo=False,             # можно True, если хочешь видеть SQL-запросы
)

# Фабрика сессий
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


@contextmanager
def get_db():
    """
    Контекстный менеджер для работы с сессией БД.

    Пример:

        from paycharm.app.database import get_db

        with get_db() as db:
            db.query(...)

    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
