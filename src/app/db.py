from collections.abc import AsyncIterator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine() -> AsyncEngine:
    settings = get_settings()
    url = settings.resolved_database_url
    kwargs: dict = {"future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            # Without StaticPool, every connection gets its own private in-memory DB.
            kwargs["poolclass"] = StaticPool
    return create_async_engine(url, **kwargs)


engine: AsyncEngine = _make_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def commit_or_rollback(db: AsyncSession) -> None:
    try:
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise


async def commit_and_refresh[T](db: AsyncSession, instance: T) -> T:
    await commit_or_rollback(db)
    await db.refresh(instance)
    return instance
