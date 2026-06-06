from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.project_member import ProjectMember
from app.models.enums import Role
from app.schemas.auth import UserRead
from app.schemas.project import ProjectRead
from app.schemas.task import TaskRead
from app.dependencies.auth import get_current_user
from sqlalchemy.orm import joinedload
from pydantic import BaseModel


class SearchResponse(BaseModel):
    projects: list[ProjectRead]
    tasks: list[TaskRead]
    users: list[UserRead]


router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    term = f"%{q}%"

    # Accessible project IDs
    if current_user.role == Role.admin:
        project_ids_q = select(Project.id)
    else:
        project_ids_q = select(ProjectMember.project_id).where(ProjectMember.user_id == current_user.id)
    accessible_ids = (await db.execute(project_ids_q)).scalars().all()

    # Projects
    projects = (await db.execute(
        select(Project).where(Project.id.in_(accessible_ids), Project.name.ilike(term)).limit(10)
    )).scalars().all()

    # Tasks
    tasks = (await db.execute(
        select(Task).options(joinedload(Task.assigned_user)).where(
            Task.project_id.in_(accessible_ids),
            or_(Task.title.ilike(term), Task.description.ilike(term)),
        ).limit(10)
    )).scalars().all()

    # Users — only visible ones
    if current_user.role == Role.admin:
        users = (await db.execute(
            select(User).where(User.name.ilike(term), User.is_active == True).limit(10)  # noqa: E712
        )).scalars().all()
    else:
        visible = (await db.execute(
            select(ProjectMember.user_id).where(ProjectMember.project_id.in_(accessible_ids)).distinct()
        )).scalars().all()
        users = (await db.execute(
            select(User).where(User.id.in_(visible), User.name.ilike(term), User.is_active == True).limit(10)  # noqa: E712
        )).scalars().all()

    # Attach task_count=0 for project results (search doesn't need counts)
    for p in projects:
        p.task_count = 0

    return SearchResponse(
        projects=[ProjectRead.model_validate(p) for p in projects],
        tasks=[TaskRead.model_validate(t) for t in tasks],
        users=[UserRead.model_validate(u) for u in users],
    )
