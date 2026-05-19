from datetime import datetime

from pydantic import BaseModel


class BaseCursorPaginationParams(BaseModel):
    cursor: datetime | None = None
    limit: int = 20
