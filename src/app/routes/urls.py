from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.url import (
    URLCreate,
    URLListParams,
    URLListResponse,
    URLPaginationParams,
    URLPaginationResponse,
    URLResponse,
    URLUpdate,
)
from app.services import url_service

router = APIRouter(prefix="/urls")


@router.get("/id/{monitored_url_id}")
async def get_by_id(
    monitored_url_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> URLResponse:
    monitored_url = await url_service.get_by_id(db, monitored_url_id)

    return URLResponse.model_validate(monitored_url)


@router.get("/list")
async def get_list_of_monitored_urls(
    params: Annotated[URLPaginationParams, Query()],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> URLPaginationResponse:
    monitored_urls = await url_service.get_paginated(db, params)
    urls_to_return = monitored_urls[: params.limit]

    cursor = None
    cursor_id = None

    if len(monitored_urls) > params.limit:
        cursor = urls_to_return[-1].created_at
        cursor_id = urls_to_return[-1].id

    urls = [URLResponse.model_validate(url) for url in urls_to_return]

    return URLPaginationResponse.model_validate(
        {"cursor": cursor, "cursor_id": cursor_id, "urls": urls}
    )


@router.post("/", status_code=201)
async def create_monitored_url(
    payload: URLCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> URLResponse:
    monitored_url = await url_service.create(db, payload)

    return URLResponse.model_validate(monitored_url)


@router.put("/id/{monitored_url_id}")
async def update_monitored_url(
    monitored_url_id: UUID,
    payload: URLUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> URLResponse:
    monitored_url = await url_service.update(db, monitored_url_id, payload)

    return URLResponse.model_validate(monitored_url)


@router.delete("/id/{monitored_url_id}", status_code=204)
async def delete_monitored_url(
    monitored_url_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    await url_service.delete(db, monitored_url_id)

    return Response(status_code=204)
