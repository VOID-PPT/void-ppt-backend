"""Job status polling API — the frontend's window into async work."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import ActiveUserDep
from src.database import get_db
from src.exceptions import NotFoundException
from src.jobs import service as job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])
DatabaseDep = Annotated[AsyncSession, Depends(get_db)]


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_type: str
    status: str
    payload: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    attempts: int
    created_at: datetime
    updated_at: datetime


@router.get(
    "/{job_id}",
    response_model=JobRead,
    status_code=status.HTTP_200_OK,
    summary="Poll job status",
    description="Current status of an async job (ingest, generation, export).",
)
async def get_job(job_id: uuid.UUID, _: ActiveUserDep, session: DatabaseDep) -> JobRead:
    job = await job_service.get_job(session, job_id)
    if job is None:
        raise NotFoundException(detail="Job not found")
    return JobRead.model_validate(job)
