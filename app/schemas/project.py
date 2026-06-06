from datetime import datetime, date
from pydantic import BaseModel
from app.models.enums import ProjectStatus
from app.schemas.auth import UserSummary


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    deadline: date
    status: ProjectStatus = ProjectStatus.active


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    deadline: date | None = None
    status: ProjectStatus | None = None


class ProjectRead(BaseModel):
    id: str
    name: str
    description: str | None
    deadline: date
    status: ProjectStatus
    owner_id: str
    task_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectDetail(ProjectRead):
    owner: UserSummary
