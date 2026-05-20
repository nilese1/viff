from datetime import datetime

from pydantic import UUID4, BaseModel, Field


class BaseCursorPaginationParams(BaseModel):
    cursor: datetime | None = None
    cursor_id: UUID4 | None = None
    limit: int = Field(default=20, ge=1, le=100)


class BaseCursorPaginationResponse(BaseModel):
    cursor: datetime | None = None
    cursor_id: UUID4 | None = None
