from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.activity_log import ActivityLog
from app.models.user import User
from app.schemas.activity import ActivityRead
from app.schemas.response import ApiResponse, ok_paginated
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=ApiResponse[list[ActivityRead]])
async def list_activity(
    project_id: str | None = Query(None),
    actor_id: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(ActivityLog).options(selectinload(ActivityLog.actor))
    if project_id:
        q = q.where(ActivityLog.project_id == project_id)
    if actor_id:
        q = q.where(ActivityLog.actor_id == actor_id)
    q = q.order_by(ActivityLog.created_at.desc())

    total: int = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    rows = (await db.execute(q.offset((page - 1) * limit).limit(limit))).scalars().all()

    return ok_paginated(
        [ActivityRead.model_validate(r) for r in rows], total, page, limit, "Activity retrieved"
    )
