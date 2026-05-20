from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.snapshot import (
    SnapshotCreate,
    SnapshotPaginationParams,
    SnapshotPaginationResponse,
    SnapshotResponse,
    SnapshotUpdate,
)
from app.services import snapshot_service

router = APIRouter(prefix="/urls/id/{monitored_url_id}/snapshots")


@router.get("/id/{snapshot_id}")
async def get_by_id(
    monitored_url_id: UUID,
    snapshot_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SnapshotResponse:
    snapshot = await snapshot_service.get_by_id(db, monitored_url_id, snapshot_id)

    return SnapshotResponse.model_validate(snapshot)


@router.get("/list")
async def get_list_of_snapshots(
    monitored_url_id: UUID,
    params: Annotated[SnapshotPaginationParams, Query()],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SnapshotPaginationResponse:
    snapshots = await snapshot_service.get_paginated(db, monitored_url_id, params)
    snapshots_to_return = snapshots[: params.limit]

    cursor = None
    cursor_id = None

    if len(snapshots) > params.limit:
        cursor = snapshots_to_return[-1].created_at
        cursor_id = snapshots_to_return[-1].id

    response_snapshots = [
        SnapshotResponse.model_validate(snapshot) for snapshot in snapshots_to_return
    ]

    return SnapshotPaginationResponse.model_validate(
        {
            "cursor": cursor,
            "cursor_id": cursor_id,
            "snapshots": response_snapshots,
        }
    )


@router.post("/", status_code=201)
async def create_snapshot(
    monitored_url_id: UUID,
    payload: SnapshotCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SnapshotResponse:
    snapshot = await snapshot_service.create(db, monitored_url_id, payload)

    return SnapshotResponse.model_validate(snapshot)


@router.put("/id/{snapshot_id}")
async def update_snapshot(
    monitored_url_id: UUID,
    snapshot_id: UUID,
    payload: SnapshotUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SnapshotResponse:
    snapshot = await snapshot_service.update(db, monitored_url_id, snapshot_id, payload)

    return SnapshotResponse.model_validate(snapshot)


@router.delete("/id/{snapshot_id}", status_code=204)
async def delete_snapshot(
    monitored_url_id: UUID,
    snapshot_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    await snapshot_service.delete(db, monitored_url_id, snapshot_id)

    return Response(status_code=204)
