import asyncio
import functools
import cloudinary.uploader
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.attachment import Attachment
from app.models.user import User
from app.models.enums import Role
from app.schemas.project import ProjectCreate, ProjectUpdate


def assert_can_modify_project(project: Project, current_user: User) -> None:
    if current_user.role == Role.admin:
        return
    if (
        current_user.role == Role.project_manager
        and project.owner_id == current_user.id
    ):
        return
    raise HTTPException(status_code=403, detail="Not authorized to modify this project")


async def list_projects(
    db: AsyncSession,
    current_user: User,
    search: str | None = None,
    status: str | None = None,
    sort_by: str = "created_at",
    page: int = 1,
    page_size: int = 20,
):
    q = select(Project)
    if current_user.role != Role.admin:
        member_projects = select(ProjectMember.project_id).where(
            ProjectMember.user_id == current_user.id
        )
        q = q.where(Project.id.in_(member_projects))
    if search:
        q = q.where(Project.name.ilike(f"%{search}%"))
    if status:
        q = q.where(Project.status == status)

    sort_col = {
        "created_at": Project.created_at,
        "deadline": Project.deadline,
        "updated_at": Project.updated_at,
    }.get(sort_by, Project.created_at)
    q = q.order_by(sort_col.desc())

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    rows = (
        (await db.execute(q.offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )

    # Attach task_count per project
    project_ids = [p.id for p in rows]
    counts = {}
    if project_ids:
        count_rows = (
            await db.execute(
                select(Task.project_id, func.count(Task.id))
                .where(Task.project_id.in_(project_ids))
                .group_by(Task.project_id)
            )
        ).all()
        counts = {r[0]: r[1] for r in count_rows}

    result = []
    for p in rows:
        p.task_count = counts.get(p.id, 0)
        result.append(p)

    return result, total


async def get_project(db: AsyncSession, project_id: str, current_user: User) -> Project:
    project = (
        await db.execute(
            select(Project)
            .options(joinedload(Project.owner))
            .where(Project.id == project_id)
        )
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != Role.admin:
        member = (
            await db.execute(
                select(ProjectMember).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == current_user.id,
                )
            )
        ).scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=403, detail="Access denied")

    count = (
        await db.execute(
            select(func.count(Task.id)).where(Task.project_id == project_id)
        )
    ).scalar()
    project.task_count = count or 0
    return project


async def create_project(
    db: AsyncSession, data: ProjectCreate, current_user: User
) -> Project:
    project = Project(**data.model_dump(), owner_id=current_user.id)
    db.add(project)
    await db.flush()
    # Add owner as a member automatically
    db.add(ProjectMember(project_id=project.id, user_id=current_user.id))
    await db.commit()
    await db.refresh(project)
    project.task_count = 0
    return project


async def update_project(
    db: AsyncSession, project_id: str, data: ProjectUpdate, current_user: User
) -> Project:
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    assert_can_modify_project(project, current_user)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    count = (
        await db.execute(
            select(func.count(Task.id)).where(Task.project_id == project_id)
        )
    ).scalar()
    project.task_count = count or 0
    return project


async def delete_project(db: AsyncSession, project_id: str, current_user: User) -> None:
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    assert_can_modify_project(project, current_user)

    # Collect Cloudinary IDs before cascade deletes rows
    result = await db.execute(
        select(Attachment.cloudinary_public_id)
        .join(Task, Task.id == Attachment.task_id)
        .where(Task.project_id == project_id)
    )
    public_ids = result.scalars().all()

    await db.delete(project)
    await db.commit()

    loop = asyncio.get_event_loop()
    for public_id in public_ids:
        await loop.run_in_executor(
            None, functools.partial(cloudinary.uploader.destroy, public_id, resource_type="raw")
        )
