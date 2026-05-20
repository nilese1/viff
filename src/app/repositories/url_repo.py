from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MonitoredURL
from app.schemas.url import URLUpdate


async def _commit_and_refresh(db: AsyncSession, monitored_url: MonitoredURL) -> MonitoredURL:
    try:
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise

    await db.refresh(monitored_url)
    return monitored_url


async def get(db: AsyncSession, monitored_url_id: UUID) -> MonitoredURL | None:
    return await db.get(MonitoredURL, monitored_url_id)


async def get_by_url(db: AsyncSession, url: str) -> MonitoredURL | None:
    result = await db.execute(select(MonitoredURL).filter_by(url=url))

    return result.scalar_one_or_none()


async def get_paginated(
    db: AsyncSession,
    search_str: str | None = None,
    *,
    cursor: datetime | None = None,
    cursor_id: UUID | None = None,
    limit: int = 20,
) -> list[MonitoredURL]:
    stmt = (
        select(MonitoredURL)
        .order_by(MonitoredURL.created_at.asc(), MonitoredURL.id.asc())
        .limit(limit + 1)
    )

    if cursor:
        if cursor_id:
            stmt = stmt.where(
                or_(
                    MonitoredURL.created_at > cursor,
                    # tiebreaker via id
                    and_(MonitoredURL.created_at == cursor, MonitoredURL.id > cursor_id),
                )
            )
        else:
            stmt = stmt.where(MonitoredURL.created_at > cursor)

    if search_str:
        stmt = stmt.where(MonitoredURL.url.icontains(search_str, autoescape=True))

    result = await db.execute(stmt)

    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    url: str,
    *,
    label: str | None = None,
    check_interval: int = 3600,
    selector_ignore: str | None = None,
    is_active: str = "Y",
    last_checked_at: datetime | None = None,
) -> MonitoredURL:
    monitored_url = MonitoredURL(
        url=url,
        label=label,
        check_interval=check_interval,
        selector_ignore=selector_ignore,
        is_active=is_active,
        last_checked_at=last_checked_at,
    )

    db.add(monitored_url)
    return await _commit_and_refresh(db, monitored_url)


async def update(
    db: AsyncSession,
    monitored_url_id: UUID,
    payload: URLUpdate,
) -> MonitoredURL | None:
    url = await get(db, monitored_url_id)

    if not url:
        return None

    update_data = payload.model_dump(exclude_unset=True, mode="json")
    for field, value in update_data.items():
        setattr(url, field, value)

    url = await _commit_and_refresh(db, url)
    return url


async def delete(db: AsyncSession, monitored_url: MonitoredURL) -> None:
    try:
        await db.delete(monitored_url)
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise


async def delete_by_id(db: AsyncSession, monitored_url_id: UUID) -> bool:
    monitored_url = await get(db, monitored_url_id)
    if monitored_url is None:
        return False

    await delete(db, monitored_url)
    return True
