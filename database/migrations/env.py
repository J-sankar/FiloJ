import os
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# 1. Import your shared Base and models so Alembic can "see" your tables
from shared.database import Base
import auth_service.models.auth# noqa: F401
import shared.models  # noqa: F401

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 2. Dynamically load the DATABASE_URL from your environment
# Fallback to local Postgres if the env var isn't set
db_url = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
)
db_schema = os.getenv("DATABASE_SCHEMA")

# ADD THIS LINE: Escape percent signs so configparser doesn't crash
db_url = db_url.replace("%", "%%")

config.set_main_option("sqlalchemy.url", db_url)

# 3. Tell Alembic to use your SQLAlchemy Metadata
target_metadata = Base.metadata

def include_name(name, type_, parent_names):
    if type_ == "schema":
        # Only scan our specific schema (e.g., 'dunno_what')
        return name == db_schema
    else:
        return True

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=db_schema,  # Isolates the tracking table
        include_schemas=True,
        include_name=include_name
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Synchronous helper to execute the migration."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema=db_schema,
        include_name=include_name
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using the asyncpg engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    

    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # 4. Execute the async migration loop
    asyncio.run(run_migrations_online())
