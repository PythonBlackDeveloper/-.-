from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# --- ВАЖНО ---
# Теперь alembic.ini лежит в КОРНЕ проекта.
# То есть структура:
#   PythonProject5/
#       alembic.ini
#       alembic/
#       paycharm/
# И Python может спокойно импортировать "paycharm" без sys.path.
# ------------------------------------------

# Импортируем настройки и Base
from paycharm.app.config import settings
from paycharm.app.models import Base


# Загружаем конфиг Alembic
config = context.config

# Подставляем URL базы в Alembic конфиг
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.unicode_string())

# Логирование Alembic
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Метаданные проекта
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
