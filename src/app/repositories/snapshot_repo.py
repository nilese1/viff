from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Snapshot


async def get(db: AsyncSession, snapshot_id: UUID) -> Snapshot | None:
    return await db.get(Snapshot, snapshot_id)


async def get_by_monitored_url(
    db: AsyncSession,
    monitored_url_id: UUID,
    snapshot_id: UUID,
) -> Snapshot | None:
    result = await db.execute(
        select(Snapshot).filter_by(
            id=snapshot_id,
            monitored_url_id=monitored_url_id,
        )
    )
    return result.scalar_one_or_none()


async def get_paginated_by_monitored_url(
    db: AsyncSession,
    monitored_url_id: UUID,
    *,
    cursor: datetime | None = None,
    cursor_id: UUID | None = None,
    limit: int = 20,
) -> list[Snapshot]:
    stmt = (
        select(Snapshot)
        .where(Snapshot.monitored_url_id == monitored_url_id)
        .order_by(Snapshot.created_at.asc(), Snapshot.id.asc())
        .limit(limit + 1)
    )

    if cursor:
        if cursor_id:
            stmt = stmt.where(
                or_(
                    Snapshot.created_at > cursor,
                    and_(Snapshot.created_at == cursor, Snapshot.id > cursor_id),
                )
            )
        else:
            stmt = stmt.where(Snapshot.created_at > cursor)

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
    return snapshot


async def update(
    db: AsyncSession,
    snapshot: Snapshot,
    **update_data: object,
) -> Snapshot:
    for field, value in update_data.items():
        setattr(snapshot, field, value)

    return snapshot


async def delete(db: AsyncSession, snapshot: Snapshot) -> None:
    await db.delete(snapshot)


async def delete_by_id(db: AsyncSession, snapshot_id: UUID) -> bool:
    snapshot = await get(db, snapshot_id)
    if snapshot is None:
        return False

    await delete(db, snapshot)
    return True
