import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.enums import Role
from app.schemas.task import TaskCreate, TaskUpdate, TaskStatusUpdate, TaskRead
from app.schemas.common import PaginatedResponse
from app.dependencies.auth import get_current_user, require_role
from app.services import task_service
from app.services.notification_service import create_notification
from app.utils.activity_logger import log_activity

router = APIRouter(tags=["tasks"])


def _task_filters(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    assigned_to: str | None = Query(None),
    deadline_status: str | None = Query(None),
    sort_by: str = Query("created_at"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return dict(status=status, priority=priority, assigned_to=assigned_to,
                deadline_status=deadline_status, sort_by=sort_by, page=page, page_size=page_size)


@router.get("/tasks", response_model=PaginatedResponse[TaskRead])
async def list_all_tasks(
    filters: dict = Depends(_task_filters),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows, total = await task_service.list_tasks(db, current_user, **filters)
    return PaginatedResponse(
        items=rows, total=total, page=filters["page"], page_size=filters["page_size"],
        total_pages=math.ceil(total / filters["page_size"]) if total else 0,
    )


@router.get("/projects/{project_id}/tasks", response_model=PaginatedResponse[TaskRead])
async def list_project_tasks(
    project_id: str,
    filters: dict = Depends(_task_filters),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows, total = await task_service.list_tasks(db, current_user, project_id=project_id, **filters)
    return PaginatedResponse(
        items=rows, total=total, page=filters["page"], page_size=filters["page_size"],
        total_pages=math.ceil(total / filters["page_size"]) if total else 0,
    )


@router.post("/projects/{project_id}/tasks", response_model=TaskRead, status_code=201)
async def create_task(
    project_id: str,
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.admin, Role.project_manager)),
):
    task = await task_service.create_task(db, project_id, body, current_user)
    await log_activity(db, current_user, "task.created", "Task", task.id, project_id, {"title": task.title})
    if task.assigned_to and task.assigned_to != current_user.id:
        await create_notification(db, task.assigned_to, f"You have been assigned: {task.title}", f"/tasks/{task.id}")
    await db.commit()
    return task


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await task_service.get_task(db, task_id, current_user)


@router.put("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: str,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.admin, Role.project_manager)),
):
    task = await task_service.update_task(db, task_id, body, current_user)
    await log_activity(db, current_user, "task.updated", "Task", task_id, task.project_id, {"title": task.title})
    if body.assigned_to and body.assigned_to != current_user.id:
        await create_notification(db, body.assigned_to, f"You have been assigned: {task.title}", f"/tasks/{task_id}")
    await db.commit()
    return task


@router.patch("/tasks/{task_id}/status", response_model=TaskRead)
async def update_task_status(
    task_id: str,
    body: TaskStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await task_service.update_task_status(db, task_id, body, current_user)
    await log_activity(db, current_user, "task.status_changed", "Task", task_id, task.project_id, {"status": body.status.value})
    await db.commit()
    return task


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.admin, Role.project_manager)),
):
    await task_service.delete_task(db, task_id, current_user)
