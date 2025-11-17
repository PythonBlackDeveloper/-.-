# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from paycharm.app.config import settings

engine = create_engine(
    settings.DATABASE_URL.unicode_string(),
    future=True,
    echo=False,  # можно True для отладки SQL
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

Base = declarative_base()


def get_db():
    from contextlib import contextmanager

    @contextmanager
    def _get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    return _get_db()
