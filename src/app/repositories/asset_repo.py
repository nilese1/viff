from datetime import datetime
from uuid import UUID

from sqlalchemy import Text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Asset, SnapshotAsset


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


async def create(
    db: AsyncSession,
    snapshot_id: UUID,
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
    snapshot_asset = SnapshotAsset(snapshot_id=snapshot_id, asset_id=asset.id)
    db.add_all(asset, snapshot_asset)
    return asset
