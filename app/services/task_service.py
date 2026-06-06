import asyncio
import cloudinary.uploader
from datetime import date
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.task import Task
from app.models.attachment import Attachment
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.enums import Role, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate, TaskStatusUpdate


async def list_tasks(
    db: AsyncSession,
    current_user: User,
    project_id: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    deadline_status: str | None = None,
    sort_by: str = "created_at",
    page: int = 1,
    page_size: int = 20,
):
    q = select(Task).options(joinedload(Task.assigned_user))

    if current_user.role != Role.admin:
        member_projects = select(ProjectMember.project_id).where(ProjectMember.user_id == current_user.id)
        q = q.where(Task.project_id.in_(member_projects))

    if project_id:
        q = q.where(Task.project_id == project_id)
    if status:
        q = q.where(Task.status == status)
    if priority:
        q = q.where(Task.priority == priority)
    if assigned_to:
        q = q.where(Task.assigned_to == assigned_to)
    if deadline_status == "overdue":
        q = q.where(Task.due_date < date.today(), Task.status != TaskStatus.completed)
    elif deadline_status == "upcoming":
        from datetime import timedelta
        q = q.where(Task.due_date >= date.today(), Task.due_date <= date.today() + timedelta(days=7))

    sort_col = {
        "created_at": Task.created_at,
        "due_date": Task.due_date,
        "priority": Task.priority,
        "updated_at": Task.updated_at,
    }.get(sort_by, Task.created_at)
    q = q.order_by(sort_col.desc())

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    rows = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return rows, total


async def get_task(db: AsyncSession, task_id: str, current_user: User) -> Task:
    task = (await db.execute(
        select(Task).options(joinedload(Task.assigned_user)).where(Task.id == task_id)
    )).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if current_user.role != Role.admin:
        member = (await db.execute(
            select(ProjectMember).where(ProjectMember.project_id == task.project_id, ProjectMember.user_id == current_user.id)
        )).scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=403, detail="Access denied")
    return task


async def create_task(db: AsyncSession, project_id: str, data: TaskCreate, current_user: User) -> Task:
    # Duplicate title check
    dup = (await db.execute(
        select(Task).where(Task.project_id == project_id, Task.title == data.title)
    )).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=409, detail="This task already exists in the project.")

    # Past due date check
    if data.due_date < date.today():
        raise HTTPException(status_code=422, detail="Please select a valid deadline.")

    task = Task(**data.model_dump(), project_id=project_id, created_by=current_user.id)
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return (await db.execute(
        select(Task).options(joinedload(Task.assigned_user)).where(Task.id == task.id)
    )).scalar_one()


async def update_task(db: AsyncSession, task_id: str, data: TaskUpdate, current_user: User) -> Task:
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Completed task re-assignment check
    if data.assigned_to is not None and task.status == TaskStatus.completed:
        raise HTTPException(status_code=422, detail="Completed tasks cannot be reassigned.")

    if data.due_date and data.due_date < date.today():
        raise HTTPException(status_code=422, detail="Please select a valid deadline.")

    if data.title and data.title != task.title:
        dup = (await db.execute(
            select(Task).where(Task.project_id == task.project_id, Task.title == data.title, Task.id != task_id)
        )).scalar_one_or_none()
        if dup:
            raise HTTPException(status_code=409, detail="This task already exists in the project.")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(task, field, value)
    await db.commit()

    return (await db.execute(
        select(Task).options(joinedload(Task.assigned_user)).where(Task.id == task_id)
    )).scalar_one()


async def update_task_status(db: AsyncSession, task_id: str, data: TaskStatusUpdate, current_user: User) -> Task:
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Only admin/PM or the assignee can update status
    if current_user.role == Role.team_member and task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update status of tasks assigned to you")

    task.status = data.status
    await db.commit()

    return (await db.execute(
        select(Task).options(joinedload(Task.assigned_user)).where(Task.id == task_id)
    )).scalar_one()


async def delete_task(db: AsyncSession, task_id: str, current_user: User) -> None:
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    public_ids = (await db.execute(
        select(Attachment.cloudinary_public_id).where(Attachment.task_id == task_id)
    )).scalars().all()

    await db.delete(task)
    await db.commit()

    loop = asyncio.get_event_loop()
    for public_id in public_ids:
        await loop.run_in_executor(None, cloudinary.uploader.destroy, public_id, {"resource_type": "raw"})
