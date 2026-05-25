from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Snapshot
from app.services import snapshot_service
from app.templating import templates

router = APIRouter()


async def _get_snapshot_pair(
    db: AsyncSession,
    left_snapshot_id: UUID | None,
    right_snapshot_id: UUID | None,
) -> tuple[Snapshot | None, Snapshot | None, list[str]]:
    left_snapshot = None
    right_snapshot = None
    messages: list[str] = []

    if left_snapshot_id:
        left_snapshot = await snapshot_service.find_by_id(db, left_snapshot_id)
        if left_snapshot is None:
            messages.append(f"Left snapshot was not found: {left_snapshot_id}")

    if right_snapshot_id:
        right_snapshot = await snapshot_service.find_by_id(db, right_snapshot_id)
        if right_snapshot is None:
            messages.append(f"Right snapshot was not found: {right_snapshot_id}")

    if bool(left_snapshot_id) ^ bool(right_snapshot_id):
        messages.append("Enter both snapshot IDs to compare them side by side.")

    return left_snapshot, right_snapshot, messages


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    left_snapshot_id: Annotated[UUID | None, Query()] = None,
    right_snapshot_id: Annotated[UUID | None, Query()] = None,
):
    left_snapshot, right_snapshot, messages = await _get_snapshot_pair(
        db,
        left_snapshot_id,
        right_snapshot_id,
    )
    context = {
        "request": request,
        "left_snapshot_id": left_snapshot_id,
        "right_snapshot_id": right_snapshot_id,
        "left_snapshot": left_snapshot,
        "right_snapshot": right_snapshot,
        "messages": messages,
    }

    if request.headers.get("hx-request") == "true":
        return templates.TemplateResponse(
            request,
            "partials/snapshot_compare_result.html",
            context,
        )

    return templates.TemplateResponse(request, "index.html", context)
