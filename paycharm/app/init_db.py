# paycharm/app/init_db.py

from __future__ import annotations

from paycharm.app.config import settings
from paycharm.app.database import engine
from paycharm.app.models import Base


def init_db() -> None:
    """
    Создаёт все таблицы в базе данных, используя SQLAlchemy.
    Без Alembic, просто create_all().
    """
    print(f"Подключаемся к базе: {settings.DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы созданы (если их не было).")


if __name__ == "__main__":
    init_db()
