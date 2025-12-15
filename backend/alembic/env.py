from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support - import the project's Base metadata
# Wrapped in try/except so environments without full deps won't fail.
try:
    from app.database import Base
    # Import models package to ensure all model modules are imported
    # so that `Base.metadata` is populated for autogenerate.
    try:
        import app.models  # noqa: F401
    except Exception:
        # If individual model imports fail, continue — metadata may be partial.
        pass

    target_metadata = Base.metadata
except Exception:
    target_metadata = None

# Load the project's settings so we can use the DATABASE_URL from .env
# This keeps Alembic using the same DB configuration as the application.
try:
    # import here so alembic commands that don't need the app can still run
    from app.config import settings

    if getattr(settings, "DATABASE_URL", None):
        config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
except Exception:
    # If importing settings fails (missing deps during some CI tasks),
    # alembic will fall back to the URL in alembic.ini
    pass

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
    """Run migrations in 'online' mode.

    This supports both sync and async engines. If the configured
    URL is an async URL (eg. contains '+asyncpg'), create an AsyncEngine
    and run migrations using `connection.run_sync`.

    """

    url = config.get_main_option("sqlalchemy.url")

    def _do_run_migrations(connection: Connection) -> None:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

    # If using an async driver (asyncpg), create an async engine and run migrations
    if url and "+asyncpg" in url:
        async_engine = create_async_engine(
            url,
            poolclass=pool.NullPool,
        )

        import asyncio

        async def _run_async_migrations() -> None:
            async with async_engine.connect() as connection:
                await connection.run_sync(_do_run_migrations)
            await async_engine.dispose()

        asyncio.run(_run_async_migrations())
    else:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            _do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
