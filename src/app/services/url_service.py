from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MonitoredURL
from app.repositories import url_repo
from app.schemas.url import URLCreate, URLPaginationParams, URLUpdate


async def get_by_id(db: AsyncSession, id: UUID) -> MonitoredURL:
    monitored_url = await url_repo.get(db, id)

    if not monitored_url:
        raise HTTPException(status_code=404, detail="URL Not Found")

    return monitored_url


async def get_by_url(db: AsyncSession, url: str) -> MonitoredURL:
    monitored_url = await url_repo.get_by_url(db, url)

    if not monitored_url:
        raise HTTPException(status_code=404, detail="URL Not Found")

    return monitored_url


async def get_paginated(
    db: AsyncSession,
    params: URLPaginationParams,
) -> list[MonitoredURL]:
    page = await url_repo.get_paginated(
        db, params.search_str, cursor=params.cursor, limit=params.limit
    )

    if len(page) <= 0:
        raise HTTPException(status_code=404, detail="No URLs found")

    return page


async def create(db: AsyncSession, payload: URLCreate) -> MonitoredURL:
    existing = await url_repo.get_by_url(db, payload.url.__str__())

    if existing:
        raise HTTPException(status_code=409, detail="URL already exists")

    return await url_repo.create(
        db,
        payload.url.__str__(),
        label=payload.label,
        check_interval=payload.check_interval,
        selector_ignore=payload.selector_ignore,
    )


async def update(db: AsyncSession, monitored_url_id: UUID, payload: URLUpdate) -> MonitoredURL:
    return await url_repo.update(db, monitored_url_id, payload)


async def delete(db: AsyncSession, monitored_url_id: UUID) -> None:
    result = await url_repo.delete_by_id(db, monitored_url_id)

    if not result:
        raise HTTPException(status_code=404, detail="URL not found")
