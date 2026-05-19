from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MonitoredURL
from app.repositories import url_repo
from app.schemas.url import URLCreate


async def create(db: AsyncSession, payload: URLCreate) -> MonitoredURL:
    existing = await url_repo.get_by_url(db, payload.url.__str__())

    print(existing)

    if existing:
        raise HTTPException(status_code=409, detail="URL already exists")

    return await url_repo.create(db, payload.url.__str__())
