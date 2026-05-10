from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import BACKEND_ROOT, get_settings

from .models import Base


def _make_engine() -> AsyncEngine:
    url = get_settings().database_url
    # Pin the sqlite path to the backend dir so uvicorn from any CWD finds it.
    prefix = "sqlite+aiosqlite:///"
    if url.startswith(prefix):
        raw = url[len(prefix) :].removeprefix("./")
        if not raw.startswith("/"):
            abs_path = (BACKEND_ROOT / raw).resolve()
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            url = f"{prefix}{abs_path}"
    return create_async_engine(url, future=True)


_engine: AsyncEngine = _make_engine()
_Session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    _engine, expire_on_commit=False
)


def engine() -> AsyncEngine:
    return _engine


async def create_all() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with _Session() as session:
        yield session
