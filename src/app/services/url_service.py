import hashlib
from datetime import UTC, datetime
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MonitoredURL
from app.repositories import snapshot_repo, url_repo
from app.schemas.url import URLCreate, URLListParams, URLPaginationParams, URLUpdate

URL_FILTER_FIELDS = {
    "url",
    "label",
    "check_interval",
    "selector_ignore",
    "is_active",
    "is_due_for_check",
}


async def get_by_id(db: AsyncSession, id: UUID) -> MonitoredURL:
    monitored_url = await url_repo.get(db, id)

    if not monitored_url:
        raise HTTPException(status_code=404, detail="URL Not Found")

    return monitored_url


async def get_by_url(db: AsyncSession, url: str) -> MonitoredURL:
    monitored_url = await url_repo.get_by_url(db, url)

    if not monitored_url:
        raise HTTPException(status_code=404, detail="URL Not Found")

    return monitored_url


async def get_paginated(
    db: AsyncSession,
    params: URLPaginationParams,
) -> list[MonitoredURL]:
    filter_data = params.model_dump(
        include=URL_FILTER_FIELDS,
        exclude_none=True,
        mode="json",
    )
    page = await url_repo.get_paginated(
        db,
        search_str=params.search_str,
        cursor=params.cursor,
        cursor_id=params.cursor_id,
        limit=params.limit,
        **filter_data,
    )

    return page


async def get_all(db: AsyncSession, params: URLListParams) -> list[MonitoredURL]:
    filter_data = params.model_dump(
        include=URL_FILTER_FIELDS,
        exclude_none=True,
        mode="json",
    )
    return await url_repo.get_all(
        db,
        search_str=params.search_str,
        **filter_data,
    )


async def create(db: AsyncSession, payload: URLCreate) -> MonitoredURL:
    existing = await url_repo.get_by_url(db, payload.url.__str__())

    if existing:
        raise HTTPException(status_code=409, detail="URL already exists")

    try:
        return await url_repo.create(
            db,
            payload.url.__str__(),
            label=payload.label,
            check_interval=payload.check_interval,
            selector_ignore=payload.selector_ignore,
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="URL already exists") from exc


async def update(db: AsyncSession, monitored_url_id: UUID, payload: URLUpdate) -> MonitoredURL:
    monitored_url = await get_by_id(db, monitored_url_id)
    update_data = URLUpdate.model_validate(payload).model_dump(
        exclude_unset=True,
        mode="json",
    )

    return await url_repo.update(db, monitored_url, **update_data)


async def delete(db: AsyncSession, monitored_url_id: UUID) -> None:
    result = await url_repo.delete_by_id(db, monitored_url_id)

    if not result:
        raise HTTPException(status_code=404, detail="URL not found")


async def scrape_url(db: AsyncSession, url: MonitoredURL, depth: int = 0):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(str(url.url))

        if depth > 10:
            raise Exception("Redirected more than 10 times please check your url")

        if response.status_code == 301:
            # so much wrong with this but good enough!
            url.url = response.headers["location"]
            await scrape_url(db, url, depth + 1)
            return

        soup = BeautifulSoup(response.text, "html.parser")

        # strip ignored selectors content is still saved in its entirety
        # but stripping the selectors is for the hash only
        # so we don't refresh if certain elements change
        if url.selector_ignore:
            for selector in url.selector_ignore.split(","):
                for tag in soup.select(selector.strip()):
                    tag.decompose()

        text_content = soup.get_text(separator="\n", strip=True)
        content_hash = hashlib.sha256(text_content.encode()).hexdigest()

        # skip if content hasn't changed
        if await snapshot_repo.get_by_content_hash(db, url.id, content_hash):
            await url_repo.update(db, url, last_checked_at=datetime.now(UTC))
            return

        await snapshot_repo.create(
            db,
            url.id,
            raw_html=response.text,
            text_content=text_content,
            content_hash=content_hash,
            http_status=response.status_code,
        )
        await url_repo.update(db, url, last_checked_at=datetime.now(UTC))

    except Exception as e:
        await snapshot_repo.create(
            db,
            url.id,
            http_status=None,
            error_message=str(e),
        )
        await url_repo.update(db, url, last_checked_at=datetime.now(UTC))
