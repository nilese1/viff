from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Snapshot

_UNSET = object()


async def _commit_and_refresh(db: AsyncSession, snapshot: Snapshot) -> Snapshot:
    try:
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise

    await db.refresh(snapshot)
    return snapshot


async def get(db: AsyncSession, snapshot_id: UUID) -> Snapshot | None:
    return await db.get(Snapshot, snapshot_id)


async def list_all(
    db: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 100,
) -> list[Snapshot]:
    stmt = select(Snapshot).order_by(Snapshot.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_by_monitored_url(
    db: AsyncSession,
    monitored_url_id: UUID,
    *,
    offset: int = 0,
    limit: int = 100,
) -> list[Snapshot]:
    stmt = (
        select(Snapshot)
        .where(Snapshot.monitored_url_id == monitored_url_id)
        .order_by(Snapshot.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_latest_by_monitored_url(
    db: AsyncSession,
    monitored_url_id: UUID,
) -> Snapshot | None:
    stmt = (
        select(Snapshot)
        .where(Snapshot.monitored_url_id == monitored_url_id)
        .order_by(Snapshot.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_content_hash(
    db: AsyncSession,
    monitored_url_id: UUID,
    content_hash: str,
) -> Snapshot | None:
    result = await db.execute(
        select(Snapshot).filter_by(
            monitored_url_id=monitored_url_id,
            content_hash=content_hash,
        )
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    monitored_url_id: UUID,
    *,
    raw_html: str | None = None,
    text_content: str | None = None,
    content_hash: str | None = None,
    http_status: int | None = None,
    error_message: str | None = None,
    notified_at: datetime | None = None,
) -> Snapshot:
    snapshot = Snapshot(
        monitored_url_id=monitored_url_id,
        raw_html=raw_html,
        text_content=text_content,
        content_hash=content_hash,
        http_status=http_status,
        error_message=error_message,
        notified_at=notified_at,
    )

    db.add(snapshot)
    return await _commit_and_refresh(db, snapshot)


async def update(
    db: AsyncSession,
    snapshot: Snapshot,
    *,
    monitored_url_id: UUID | None = None,
    raw_html: str | None | object = _UNSET,
    text_content: str | None | object = _UNSET,
    content_hash: str | None | object = _UNSET,
    http_status: int | None | object = _UNSET,
    error_message: str | None | object = _UNSET,
    notified_at: datetime | None | object = _UNSET,
) -> Snapshot:
    if monitored_url_id is not None:
        snapshot.monitored_url_id = monitored_url_id
    if raw_html is not _UNSET:
        snapshot.raw_html = cast(str | None, raw_html)
    if text_content is not _UNSET:
        snapshot.text_content = cast(str | None, text_content)
    if content_hash is not _UNSET:
        snapshot.content_hash = cast(str | None, content_hash)
    if http_status is not _UNSET:
        snapshot.http_status = cast(int | None, http_status)
    if error_message is not _UNSET:
        snapshot.error_message = cast(str | None, error_message)
    if notified_at is not _UNSET:
        snapshot.notified_at = cast(datetime | None, notified_at)

    return await _commit_and_refresh(db, snapshot)


async def delete(db: AsyncSession, snapshot: Snapshot) -> None:
    try:
        await db.delete(snapshot)
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise


async def delete_by_id(db: AsyncSession, snapshot_id: UUID) -> bool:
    snapshot = await get(db, snapshot_id)
    if snapshot is None:
        return False

    await delete(db, snapshot)
    return True
