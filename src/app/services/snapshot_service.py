from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Snapshot
from app.repositories import snapshot_repo, url_repo
from app.schemas.snapshot import SnapshotCreate, SnapshotPaginationParams, SnapshotUpdate


async def _ensure_monitored_url_exists(db: AsyncSession, monitored_url_id: UUID) -> None:
    monitored_url = await url_repo.get(db, monitored_url_id)

    if not monitored_url:
        raise HTTPException(status_code=404, detail="URL not found")


async def get_by_id(
    db: AsyncSession,
    monitored_url_id: UUID,
    snapshot_id: UUID,
) -> Snapshot:
    snapshot = await snapshot_repo.get_by_monitored_url(db, monitored_url_id, snapshot_id)

    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    return snapshot


async def get_paginated(
    db: AsyncSession,
    monitored_url_id: UUID,
    params: SnapshotPaginationParams,
) -> list[Snapshot]:
    await _ensure_monitored_url_exists(db, monitored_url_id)

    page = await snapshot_repo.get_paginated_by_monitored_url(
        db,
        monitored_url_id,
        cursor=params.cursor,
        cursor_id=params.cursor_id,
        limit=params.limit,
    )

    return page


async def create(
    db: AsyncSession,
    monitored_url_id: UUID,
    payload: SnapshotCreate,
) -> Snapshot:
    await _ensure_monitored_url_exists(db, monitored_url_id)

    try:
        return await snapshot_repo.create(
            db,
            monitored_url_id,
            raw_html=payload.raw_html,
            text_content=payload.text_content,
            content_hash=payload.content_hash,
            http_status=payload.http_status,
            error_message=payload.error_message,
            notified_at=payload.notified_at,
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Snapshot already exists for this content hash",
        ) from exc


async def update(
    db: AsyncSession,
    monitored_url_id: UUID,
    snapshot_id: UUID,
    payload: SnapshotUpdate,
) -> Snapshot:
    snapshot = await get_by_id(db, monitored_url_id, snapshot_id)
    update_data = SnapshotUpdate.model_validate(payload).model_dump(exclude_unset=True)

    try:
        return await snapshot_repo.update(db, snapshot, **update_data)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Snapshot already exists for this content hash",
        ) from exc


async def delete(db: AsyncSession, monitored_url_id: UUID, snapshot_id: UUID) -> None:
    snapshot = await get_by_id(db, monitored_url_id, snapshot_id)
    await snapshot_repo.delete(db, snapshot)
