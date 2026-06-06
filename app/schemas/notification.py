from datetime import datetime
from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: str
    message: str
    is_read: bool
    link: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    count: int
