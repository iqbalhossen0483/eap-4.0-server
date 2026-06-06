from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.models.enums import Role, TaskStatus, Priority
from app.schemas.dashboard import (
    KPIStats, ProjectSummary, TasksByPriority, TaskStatusDistribution,
    TeamProductivity, UpcomingDeadline, HighPriorityTask, DashboardResponse,
)
from app.schemas.auth import UserSummary
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def _accessible_project_ids(db: AsyncSession, current_user: User) -> list[str]:
    if current_user.role == Role.admin:
        rows = (await db.execute(select(Project.id))).scalars().all()
    else:
        rows = (await db.execute(
            select(ProjectMember.project_id).where(ProjectMember.user_id == current_user.id)
        )).scalars().all()
    return list(rows)


async def _get_kpi(db: AsyncSession, project_ids: list[str]) -> KPIStats:
    total_projects = len(project_ids)
    if not project_ids:
        return KPIStats(total_projects=0, total_tasks=0, completed_tasks=0, pending_tasks=0, overdue_tasks=0)

    total_tasks = (await db.execute(select(func.count(Task.id)).where(Task.project_id.in_(project_ids)))).scalar() or 0
    completed = (await db.execute(select(func.count(Task.id)).where(Task.project_id.in_(project_ids), Task.status == TaskStatus.completed))).scalar() or 0
    overdue = (await db.execute(select(func.count(Task.id)).where(Task.project_id.in_(project_ids), Task.due_date < date.today(), Task.status != TaskStatus.completed))).scalar() or 0
    return KPIStats(
        total_projects=total_projects,
        total_tasks=total_tasks,
        completed_tasks=completed,
        pending_tasks=total_tasks - completed,
        overdue_tasks=overdue,
    )


async def _get_project_summaries(db: AsyncSession, project_ids: list[str]) -> list[ProjectSummary]:
    if not project_ids:
        return []
    projects = (await db.execute(select(Project).where(Project.id.in_(project_ids)))).scalars().all()
    result = []
    for p in projects:
        total = (await db.execute(select(func.count(Task.id)).where(Task.project_id == p.id))).scalar() or 0
        completed = (await db.execute(select(func.count(Task.id)).where(Task.project_id == p.id, Task.status == TaskStatus.completed))).scalar() or 0
        result.append(ProjectSummary(
            id=p.id, name=p.name, status=p.status, deadline=p.deadline,
            task_count=total, completed_count=completed,
            completion_percent=round(completed / total * 100, 1) if total else 0.0,
        ))
    return result


async def _get_tasks_by_priority(db: AsyncSession, project_ids: list[str]) -> list[TasksByPriority]:
    if not project_ids:
        return []
    rows = (await db.execute(
        select(Task.priority, func.count(Task.id)).where(Task.project_id.in_(project_ids)).group_by(Task.priority)
    )).all()
    return [TasksByPriority(priority=r[0], count=r[1]) for r in rows]


async def _get_task_status_distribution(db: AsyncSession, project_ids: list[str]) -> list[TaskStatusDistribution]:
    if not project_ids:
        return []
    rows = (await db.execute(
        select(Task.status, func.count(Task.id)).where(Task.project_id.in_(project_ids)).group_by(Task.status)
    )).all()
    return [TaskStatusDistribution(status=r[0], count=r[1]) for r in rows]


async def _get_team_productivity(db: AsyncSession, project_ids: list[str]) -> list[TeamProductivity]:
    if not project_ids:
        return []
    member_ids = (await db.execute(
        select(ProjectMember.user_id).where(ProjectMember.project_id.in_(project_ids)).distinct()
    )).scalars().all()
    if not member_ids:
        return []

    users = (await db.execute(select(User).where(User.id.in_(member_ids)))).scalars().all()
    result = []
    for user in users:
        total = (await db.execute(select(func.count(Task.id)).where(Task.assigned_to == user.id, Task.project_id.in_(project_ids)))).scalar() or 0
        completed = (await db.execute(select(func.count(Task.id)).where(Task.assigned_to == user.id, Task.project_id.in_(project_ids), Task.status == TaskStatus.completed))).scalar() or 0
        result.append(TeamProductivity(
            user=UserSummary.model_validate(user), role=user.role, total=total, completed=completed, pending=total - completed
        ))
    return result


async def _get_upcoming_deadlines(db: AsyncSession, project_ids: list[str]) -> list[UpcomingDeadline]:
    if not project_ids:
        return []
    cutoff = date.today() + timedelta(days=7)
    tasks = (await db.execute(
        select(Task).options(joinedload(Task.project)).where(
            Task.project_id.in_(project_ids),
            Task.due_date >= date.today(),
            Task.due_date <= cutoff,
            Task.status != TaskStatus.completed,
        ).order_by(Task.due_date)
    )).scalars().all()
    return [UpcomingDeadline(id=t.id, title=t.title, due_date=t.due_date, entity_type="task", project_name=t.project.name) for t in tasks]


async def _get_high_priority_tasks(db: AsyncSession, project_ids: list[str]) -> list[HighPriorityTask]:
    if not project_ids:
        return []
    tasks = (await db.execute(
        select(Task).options(joinedload(Task.project)).where(
            Task.project_id.in_(project_ids),
            Task.priority == Priority.high,
            Task.status != TaskStatus.completed,
        ).order_by(Task.due_date).limit(10)
    )).scalars().all()
    return [HighPriorityTask(id=t.id, title=t.title, project_id=t.project_id, project_name=t.project.name, priority=t.priority, status=t.status, due_date=t.due_date) for t in tasks]


@router.get("", response_model=DashboardResponse)
async def get_dashboard(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    project_ids = await _accessible_project_ids(db, current_user)
    return DashboardResponse(
        kpi=await _get_kpi(db, project_ids),
        project_summaries=await _get_project_summaries(db, project_ids),
        tasks_by_priority=await _get_tasks_by_priority(db, project_ids),
        task_status_distribution=await _get_task_status_distribution(db, project_ids),
        team_productivity=await _get_team_productivity(db, project_ids),
        upcoming_deadlines=await _get_upcoming_deadlines(db, project_ids),
        high_priority_tasks=await _get_high_priority_tasks(db, project_ids),
    )


@router.get("/kpi", response_model=KPIStats)
async def get_kpi(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    project_ids = await _accessible_project_ids(db, current_user)
    return await _get_kpi(db, project_ids)


@router.get("/project-summaries", response_model=list[ProjectSummary])
async def get_project_summaries(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    project_ids = await _accessible_project_ids(db, current_user)
    return await _get_project_summaries(db, project_ids)


@router.get("/tasks-by-priority", response_model=list[TasksByPriority])
async def get_tasks_by_priority(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    project_ids = await _accessible_project_ids(db, current_user)
    return await _get_tasks_by_priority(db, project_ids)


@router.get("/task-status-distribution", response_model=list[TaskStatusDistribution])
async def get_task_status_distribution(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    project_ids = await _accessible_project_ids(db, current_user)
    return await _get_task_status_distribution(db, project_ids)


@router.get("/team-productivity", response_model=list[TeamProductivity])
async def get_team_productivity(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    project_ids = await _accessible_project_ids(db, current_user)
    return await _get_team_productivity(db, project_ids)


@router.get("/upcoming-deadlines", response_model=list[UpcomingDeadline])
async def get_upcoming_deadlines(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    project_ids = await _accessible_project_ids(db, current_user)
    return await _get_upcoming_deadlines(db, project_ids)


@router.get("/high-priority-tasks", response_model=list[HighPriorityTask])
async def get_high_priority_tasks(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    project_ids = await _accessible_project_ids(db, current_user)
    return await _get_high_priority_tasks(db, project_ids)
