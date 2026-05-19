from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict, HttpUrl


class URLBase(BaseModel):
    url: HttpUrl
    label: str | None = None
    check_interval: int = 3600
    selector_ignore: str | None = None


class URLCreate(URLBase):
    pass  # just what the client sends on POST


class URLUpdate(BaseModel):
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
