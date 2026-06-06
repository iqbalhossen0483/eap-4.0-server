from datetime import datetime
from pydantic import BaseModel
from app.schemas.auth import UserSummary


class CommentCreate(BaseModel):
    body: str


class CommentRead(BaseModel):
    id: str
    task_id: str
    body: str
    author: UserSummary
    created_at: datetime

    model_config = {"from_attributes": True}
