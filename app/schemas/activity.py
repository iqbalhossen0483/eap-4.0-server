from datetime import datetime
from pydantic import BaseModel
from app.schemas.auth import UserSummary


class ActivityRead(BaseModel):
    id: str
    actor: UserSummary
    action: str
    entity_type: str
    entity_id: str
    project_id: str | None
    detail: dict
    created_at: datetime

    model_config = {"from_attributes": True}
