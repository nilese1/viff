import hashlib
import uuid
from datetime import UTC, datetime
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.archive.assets import FetchedResource, fetch_same_origin_assets
from app.archive.storage import build_object_key, get_archive_storage
from app.archive.warc import build_warc
from app.db import commit_and_refresh, commit_or_rollback
from app.models import MonitoredURL, Snapshot
from app.repositories import asset_repo, snapshot_repo, url_repo
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
        monitored_url = await url_repo.create(
            db,
            payload.url.__str__(),
            label=payload.label,
            check_interval=payload.check_interval,
            selector_ignore=payload.selector_ignore,
        )
        return await commit_and_refresh(db, monitored_url)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="URL already exists") from exc


async def update(db: AsyncSession, monitored_url_id: UUID, payload: URLUpdate) -> MonitoredURL:
    monitored_url = await get_by_id(db, monitored_url_id)
    update_data = URLUpdate.model_validate(payload).model_dump(
        exclude_unset=True,
        mode="json",
    )

    monitored_url = await url_repo.update(db, monitored_url, **update_data)
    return await commit_and_refresh(db, monitored_url)


async def delete(db: AsyncSession, monitored_url_id: UUID) -> None:
    result = await url_repo.delete_by_id(db, monitored_url_id)

    if not result:
        raise HTTPException(status_code=404, detail="URL not found")

    await commit_or_rollback(db)


# TODO: make sure that asset hashes are being compared even when page content hasn't changed
async def scrape_url(db: AsyncSession, url: MonitoredURL):
    try:
        snapshot: Snapshot = None

        async with httpx.AsyncClient(timeout=10, follow_redirects=True, max_redirects=10) as client:
            response = await client.get(str(url.url))

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
                return

            snapshot_id = uuid.uuid4()

            warc_storage_key = build_object_key(
                "snapshots",
                url.id,
                snapshot_id,
                "archive.warc.gz",
            )
            storage = get_archive_storage()

            page_resource = FetchedResource(
                url=str(response.url),
                status_code=response.status_code,
                reason_phrase=response.reason_phrase,
                headers=tuple((key, value) for key, value in response.headers.items()),
                content=response.content,
            )
            asset_resources = await fetch_same_origin_assets(
                client,
                response.text,
                str(response.url),
            )
            warc_bytes = build_warc([page_resource])
            await storage.put_bytes(warc_storage_key, warc_bytes, "application/warc+gzip")

            snapshot = await snapshot_repo.create(
                db,
                url.id,
                id=snapshot_id,
                text_content=text_content,
                content_hash=content_hash,
                http_status=response.status_code,
            )
            await db.flush()

            # seperating the warc by resource rather than all of the resources at once
            # to make the archive more resilient to individual changes per
            # asset, this goes against warc's main philosophy of keeping
            # assets local to each archive so might change this once
            # profiling is set up if there's no noticable difference
            # in storage size given volatile assets
            #
            # tl;dr doing easy shit the hard way because I have no idea
            # what I'm doing
            for resource in asset_resources:
                content_hash = hashlib.sha256(resource.content).hexdigest()

                # resource already exists
                if await asset_repo.get_by_content_hash(db, url.id, content_hash):
                    continue

                resource_id = uuid.uuid4()

                warc_storage_key = build_object_key(
                    "snapshots",
                    url.id,
                    snapshot.id,
                    resource_id,
                    "asset-archive.warc.gz",
                )

                warc_bytes = build_warc([resource])
                await storage.put_bytes(warc_storage_key, warc_bytes, "application/warc+gzip")

                await asset_repo.create(
                    db,
                    snapshot.id,
                    url.id,
                    id=resource_id,
                    label=resource.url,
                    warc_storage_key=warc_storage_key,
                    content_hash=content_hash,
                    http_status=resource.status_code,
                )

    except Exception as e:
        if snapshot is None:
            snapshot = await snapshot_repo.create(
                db,
                url.id,
                http_status=None,
                error_message=str(e),
            )
        else:
            await snapshot_repo.update(
                db, snapshot, update_data={"http_status": None, "error_message": str(e)}
            )
        await db.flush()

        await asset_repo.create(
            db,
            snapshot.id,
            url.id,
            http_status=None,
            error_message=str(e),
        )

    await url_repo.update(db, url, last_checked_at=datetime.now(UTC))
    await commit_or_rollback(db)
