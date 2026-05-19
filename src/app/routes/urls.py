from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.url import URLCreate, URLPaginationParams, URLUpdate
from app.services import url_service

router = APIRouter(prefix="/urls")


@router.get("/id/{monitored_url_id}")
async def get_by_id(
    monitored_url_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    return await url_service.get_by_id(db, monitored_url_id)


@router.get("/list")
async def get_router_list(
    params: Annotated[URLPaginationParams, Query()],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    return await url_service.get_paginated(db, params)


@router.post("/")
async def create_monitored_url(
    payload: URLCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    return await url_service.create(db, payload)


@router.post("/id/{monitored_url_id}")
async def update_monitored_url(
    monitored_url_id: UUID,
    payload: URLUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    return await url_service.update(db, monitored_url_id, payload)


@router.delete("/id/{monitored_url_id}")
async def delete_monitored_url(
    monitored_url_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    return await url_service.delete(db, monitored_url_id)
