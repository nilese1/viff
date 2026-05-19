from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.url import URLCreate
from app.services import url_service

router = APIRouter(prefix="/urls")


@router.post("/")
async def create_monitored_url(payload: URLCreate, db: AsyncSession = Depends(get_session)):
    return await url_service.create(db, payload)
