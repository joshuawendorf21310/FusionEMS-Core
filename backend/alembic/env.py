from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from core_app.core.config import get_settings
from core_app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    # Prefer explicit env var if present; otherwise load from app settings.
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    return get_settings().database_url


def _make_sync_url(url: str) -> str:
    """Convert async DB URL to sync for Alembic."""
    return (
        url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
           .replace("postgresql+aiopg://", "postgresql+psycopg2://")
    )


def run_migrations_offline() -> None:
    url = _make_sync_url(get_url())
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _make_sync_url(get_url())

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
