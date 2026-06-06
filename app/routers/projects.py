import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.enums import Role
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectRead
from app.schemas.member import AddMemberRequest, MemberRead
from app.schemas.common import PaginatedResponse
from app.dependencies.auth import get_current_user, require_role
from app.services import project_service, member_service
from app.utils.activity_logger import log_activity

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=PaginatedResponse[ProjectRead])
async def list_projects(
    search: str | None = Query(None),
    status: str | None = Query(None),
    sort_by: str = Query("created_at"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows, total = await project_service.list_projects(db, current_user, search, status, sort_by, page, page_size)
    return PaginatedResponse(
        items=rows, total=total, page=page, page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 0,
    )


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.admin, Role.project_manager)),
):
    project = await project_service.create_project(db, body, current_user)
    await log_activity(db, current_user, "project.created", "Project", project.id, project.id, {"name": project.name})
    await db.commit()
    return project


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await project_service.get_project(db, project_id, current_user)


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await project_service.update_project(db, project_id, body, current_user)
    await log_activity(db, current_user, "project.updated", "Project", project_id, project_id, {"name": project.name})
    await db.commit()
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await project_service.delete_project(db, project_id, current_user)


@router.get("/{project_id}/members", response_model=list[MemberRead])
async def list_members(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await member_service.list_members(db, project_id, current_user)


@router.post("/{project_id}/members", response_model=MemberRead, status_code=201)
async def add_member(
    project_id: str,
    body: AddMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.admin, Role.project_manager)),
):
    member = await member_service.add_member(db, project_id, body.user_id, current_user)
    await log_activity(db, current_user, "member.added", "ProjectMember", body.user_id, project_id, {"user_id": body.user_id})
    await db.commit()
    return member


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def remove_member(
    project_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.admin, Role.project_manager)),
):
    await member_service.remove_member(db, project_id, user_id, current_user)
