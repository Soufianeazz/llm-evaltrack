import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from storage.models import Base

# Prod: DATABASE_URL aus Env (z.B. sqlite+aiosqlite:////data/llm_observe.db auf Railway-Volume)
# Local: fällt auf Arbeitsverzeichnis zurück.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./observability.db")

engine = create_async_engine(DATABASE_URL, echo=False)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add new columns to existing tables (safe no-op if already present)
        for table, col_def in [
            ("requests", "api_key TEXT"),
            ("traces", "api_key TEXT"),
        ]:
            try:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_def}"))
            except Exception:
                pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionFactory() as session:
        yield session


@asynccontextmanager
async def get_session_ctx() -> AsyncSession:
    async with SessionFactory() as session:
        yield session
