from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MonitoredURL


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


def _apply_url_filters(
    stmt,
    *,
    search_str: str | None = None,
    url: str | None = None,
    label: str | None = None,
    check_interval: int | None = None,
    selector_ignore: str | None = None,
    is_active: str | None = None,
):
    if search_str:
        stmt = stmt.where(MonitoredURL.url.icontains(search_str, autoescape=True))

    if url is not None:
        stmt = stmt.where(MonitoredURL.url == url)

    if label is not None:
        stmt = stmt.where(MonitoredURL.label == label)

    if check_interval is not None:
        stmt = stmt.where(MonitoredURL.check_interval == check_interval)

    if selector_ignore is not None:
        stmt = stmt.where(MonitoredURL.selector_ignore == selector_ignore)

    if is_active is not None:
        stmt = stmt.where(MonitoredURL.is_active == is_active)

    return stmt


def _is_due_for_check(monitored_url: MonitoredURL, now: datetime) -> bool:
    if monitored_url.last_checked_at is None:
        return True

    now_for_comparison = now
    if monitored_url.last_checked_at.tzinfo is None:
        now_for_comparison = now.replace(tzinfo=None)

    next_check_at = monitored_url.last_checked_at + timedelta(seconds=monitored_url.check_interval)
    return next_check_at <= now_for_comparison


# WARNING: codex really wanted to do this outside of the query but this is probably slow
def _apply_due_filter(
    monitored_urls: list[MonitoredURL],
    *,
    is_due_for_check: bool | None = None,
) -> list[MonitoredURL]:
    if is_due_for_check is None:
        return monitored_urls

    now = datetime.now(UTC)
    return [
        monitored_url
        for monitored_url in monitored_urls
        if _is_due_for_check(monitored_url, now) is is_due_for_check
    ]


async def get_paginated(
    db: AsyncSession,
    *,
    search_str: str | None = None,
    cursor: datetime | None = None,
    cursor_id: UUID | None = None,
    limit: int = 20,
    url: str | None = None,
    label: str | None = None,
    check_interval: int | None = None,
    selector_ignore: str | None = None,
    is_active: str | None = None,
    is_due_for_check: bool | None = None,
) -> list[MonitoredURL]:
    stmt = select(MonitoredURL).order_by(MonitoredURL.created_at.asc(), MonitoredURL.id.asc())

    if cursor and cursor_id:
        stmt = stmt.where(
            or_(
                MonitoredURL.created_at > cursor,
                # tiebreaker via id
                and_(MonitoredURL.created_at == cursor, MonitoredURL.id > cursor_id),
            )
        )
    elif cursor:
        stmt = stmt.where(MonitoredURL.created_at > cursor)

    stmt = _apply_url_filters(
        stmt,
        search_str=search_str,
        url=url,
        label=label,
        check_interval=check_interval,
        selector_ignore=selector_ignore,
        is_active=is_active,
    )

    result = await db.execute(stmt)

    monitored_urls = _apply_due_filter(
        list(result.scalars().all()),
        is_due_for_check=is_due_for_check,
    )
    return monitored_urls[: limit + 1]


async def get_all(
    db: AsyncSession,
    *,
    search_str: str | None = None,
    url: str | None = None,
    label: str | None = None,
    check_interval: int | None = None,
    selector_ignore: str | None = None,
    is_active: str | None = None,
    is_due_for_check: bool | None = None,
) -> list[MonitoredURL]:
    stmt = select(MonitoredURL).order_by(MonitoredURL.created_at.asc(), MonitoredURL.id.asc())
    stmt = _apply_url_filters(
        stmt,
        search_str=search_str,
        url=url,
        label=label,
        check_interval=check_interval,
        selector_ignore=selector_ignore,
        is_active=is_active,
    )

    result = await db.execute(stmt)

    return _apply_due_filter(
        list(result.scalars().all()),
        is_due_for_check=is_due_for_check,
    )


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
    monitored_url: MonitoredURL,
    **update_data: object,
) -> MonitoredURL:
    for field, value in update_data.items():
        setattr(monitored_url, field, value)

    return await _commit_and_refresh(db, monitored_url)


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
