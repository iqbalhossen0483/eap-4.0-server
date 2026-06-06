from datetime import datetime, date
from pydantic import BaseModel
from app.models.enums import TaskStatus, Priority
from app.schemas.auth import UserSummary


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    assigned_to: str | None = None
    due_date: date
    priority: Priority = Priority.medium
    status: TaskStatus = TaskStatus.todo


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assigned_to: str | None = None
    due_date: date | None = None
    priority: Priority | None = None
    status: TaskStatus | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskRead(BaseModel):
    id: str
    title: str
    description: str | None
    project_id: str
    assigned_to: str | None
    assigned_user: UserSummary | None = None
    due_date: date
    priority: Priority
    status: TaskStatus
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
