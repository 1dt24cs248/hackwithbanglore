from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import Settings
from app.models import Base  # noqa: F401; importing registers all models


config = context.config
target_metadata = Base.metadata


def _database_url() -> str:
    configured_url = config.get_main_option("sqlalchemy.url")
    if not configured_url:
        configured_url = Settings.load().require_database()
    # Alembic Config uses ConfigParser interpolation; escape URL percent signs.
    config.set_main_option("sqlalchemy.url", configured_url.replace("%", "%%"))
    return configured_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = config.attributes.get("connection")
    if connectable is not None:
        with connectable.begin():
            context.configure(
                connection=connectable,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
        return

    _database_url()
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
