from datetime import datetime
from uuid import UUID

from sqlalchemy import Text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Asset, SnapshotAsset


async def get(db: AsyncSession, asset_id: UUID) -> Asset | None:
    return await db.get(Asset, asset_id)


async def get_by_content_hash(
    db: AsyncSession,
    monitored_url_id: UUID,
    content_hash: str,
) -> Asset | None:
    result = await db.execute(
        select(Asset).filter_by(
            monitored_url_id=monitored_url_id,
            content_hash=content_hash,
        )
    )
    return result.scalar_one_or_none()


async def get_all_by_snapshot_id(
    db: AsyncSession,
    snapshot_id: UUID,
) -> list[Asset]:
    result = await db.execute(
        select(SnapshotAsset).filter_by(
            snapshot_id=snapshot_id,
        )
    )

    snapshot_assets: list[SnapshotAsset] = list(result.scalars().all())

    assets: list[Asset] = []

    for snapshot_asset in snapshot_assets:
        assets.append(await get(db, snapshot_asset.asset_id))

    return assets


async def create(
    db: AsyncSession,
    snapshot_id: UUID,
    monitored_url_id: UUID,
    *,
    id: UUID | None = None,
    label: str | None = None,
    warc_storage_key: str | None = None,
    content_hash: str | None = None,
    http_status: int | None = None,
    error_message: Text | None = None,
    notified_at: datetime | None = None,
) -> Asset:
    asset_data = {
        "monitored_url_id": monitored_url_id,
        "label": label,
        "warc_storage_key": warc_storage_key,
        "content_hash": content_hash,
        "http_status": http_status,
        "error_message": error_message,
        "notified_at": notified_at,
    }
    if id is not None:
        asset_data["id"] = id

    asset = Asset(**asset_data)
    db.add(asset)
    await db.flush()

    snapshot_asset = SnapshotAsset(snapshot_id=snapshot_id, asset_id=asset.id)
    db.add(snapshot_asset)

    return asset
