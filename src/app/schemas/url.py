from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict, HttpUrl

from app.schemas.base import (
    BaseCursorPaginationParams,
    BaseCursorPaginationResponse,
)


class URLBase(BaseModel):
    url: HttpUrl
    label: str | None = None
    check_interval: int = 3600
    selector_ignore: str | None = None


class URLCreate(URLBase):
    pass  # just what the client sends on POST


class URLUpdate(BaseModel):
    url: HttpUrl | None = None
    label: str | None = None
    check_interval: int | None = None
    selector_ignore: str | None = None
    is_active: str | None = None


class URLResponse(URLBase):
    id: UUID4
    is_active: str
    last_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class URLFilterParams(BaseModel):
    search_str: str | None = None
    url: HttpUrl | None = None
    label: str | None = None
    check_interval: int | None = None
    selector_ignore: str | None = None
    last_checked_at: datetime | None = None
    is_active: str | None = None
    is_due_for_check: bool | None = None


class URLPaginationParams(URLFilterParams, BaseCursorPaginationParams):
    pass


class URLPaginationResponse(BaseCursorPaginationResponse):
    urls: list[URLResponse]


class URLListParams(URLFilterParams):
    pass


class URLListResponse(BaseModel):
    urls: list[URLResponse]
