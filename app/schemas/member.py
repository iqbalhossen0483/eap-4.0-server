from datetime import datetime
from pydantic import BaseModel
from app.models.enums import Role
from app.schemas.auth import UserSummary


class AddMemberRequest(BaseModel):
    user_id: str


class MemberRead(BaseModel):
    user_id: str
    project_id: str
    joined_at: datetime
    user: UserSummary

    model_config = {"from_attributes": True}


class WorkloadSummary(BaseModel):
    user: UserSummary
    role: Role
    total: int
    completed: int
    pending: int
