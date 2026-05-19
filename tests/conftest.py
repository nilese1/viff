import os

os.environ.setdefault("APP_ENV", "test")

from collections.abc import AsyncIterator  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app import db as db_module  # noqa: E402
from app import models as _models  # noqa: F401, E402
from app.db import Base  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with db_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with db_module.SessionLocal() as session:
        yield session

    async with db_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with db_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    async with db_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
