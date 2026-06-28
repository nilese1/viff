from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict

from app.schemas.base import (
    BaseCursorPaginationParams,
    BaseCursorPaginationResponse,
)


class SnapshotBase(BaseModel):
    text_content: str | None = None
    content_hash: str | None = None
    http_status: int | None = None
    error_message: str | None = None
    notified_at: datetime | None = None


class SnapshotCreate(SnapshotBase):
    pass


class SnapshotUpdate(SnapshotBase):
    pass


class SnapshotResponse(SnapshotBase):
    id: UUID4
    monitored_url_id: UUID4
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SnapshotPaginationParams(BaseCursorPaginationParams):
    pass


class SnapshotPaginationResponse(BaseCursorPaginationResponse):
    snapshots: list[SnapshotResponse]
