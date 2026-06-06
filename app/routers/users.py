import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.project_member import ProjectMember
from app.models.enums import Role
from app.schemas.auth import UserRead
from app.schemas.common import PaginatedResponse
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=PaginatedResponse[UserRead])
async def list_users(
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(User).where(User.is_active == True)  # noqa: E712

    if current_user.role != Role.admin:
        # PM/member can only see users who share at least one project with them
        their_projects = select(ProjectMember.project_id).where(ProjectMember.user_id == current_user.id)
        visible_users = select(ProjectMember.user_id).where(ProjectMember.project_id.in_(their_projects))
        q = q.where(or_(User.id == current_user.id, User.id.in_(visible_users)))

    if search:
        q = q.where(or_(User.name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))

    total: int = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    rows = (await db.execute(q.order_by(User.name).offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return PaginatedResponse(
        items=list(rows),
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 0,
    )
