from datetime import datetime
from pydantic import BaseModel
from app.schemas.auth import UserSummary


class AttachmentRead(BaseModel):
    id: str
    task_id: str
    original_filename: str
    cloudinary_url: str
    file_size: int
    uploaded_by: UserSummary
    created_at: datetime

    model_config = {"from_attributes": True}
