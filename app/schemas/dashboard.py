from datetime import date
from pydantic import BaseModel
from app.models.enums import ProjectStatus, TaskStatus, Priority
from app.schemas.auth import UserSummary
from app.models.enums import Role


class KPIStats(BaseModel):
    total_projects: int
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks: int


class ProjectSummary(BaseModel):
    id: str
    name: str
    status: ProjectStatus
    deadline: date
    task_count: int
    completed_count: int
    completion_percent: float


class TasksByPriority(BaseModel):
    priority: Priority
    count: int


class TaskStatusDistribution(BaseModel):
    status: TaskStatus
    count: int


class TeamProductivity(BaseModel):
    user: UserSummary
    role: Role
    total: int
    completed: int
    pending: int


class UpcomingDeadline(BaseModel):
    id: str
    title: str
    due_date: date
    entity_type: str  # "task" or "project"
    project_name: str | None = None


class HighPriorityTask(BaseModel):
    id: str
    title: str
    project_id: str
    project_name: str
    priority: Priority
    status: TaskStatus
    due_date: date


class DashboardResponse(BaseModel):
    kpi: KPIStats
    project_summaries: list[ProjectSummary]
    tasks_by_priority: list[TasksByPriority]
    task_status_distribution: list[TaskStatusDistribution]
    team_productivity: list[TeamProductivity]
    upcoming_deadlines: list[UpcomingDeadline]
    high_priority_tasks: list[HighPriorityTask]
