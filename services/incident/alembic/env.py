import asyncio
from collections.abc import Mapping

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

import app.incidents.models  # noqa: F401
from app.core.config import DatabaseSettings
from app.core.db import Base

database_url = DatabaseSettings().database_url


def include_name(
    name: str | None, type_: str, _parent_names: Mapping[str, str]
) -> bool:
    return type_ != "schema" or name == "incidents"


def migrate(connection: Connection | None = None) -> None:
    context.configure(
        connection=connection,
        url=database_url,
        target_metadata=Base.metadata,
        include_schemas=True,
        include_name=include_name,
        version_table_schema="public",
        literal_binds=connection is None,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(database_url, poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(migrate)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    migrate()
else:
    asyncio.run(run_migrations_online())
