from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import Role

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.project_member import ProjectMember
    from app.models.task import Task
    from app.models.comment import Comment
    from app.models.attachment import Attachment
    from app.models.notification import Notification


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[Role] = mapped_column(SAEnum(Role), nullable=False, default=Role.team_member)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    projects_owned: Mapped[list["Project"]] = relationship("Project", back_populates="owner", foreign_keys="Project.owner_id")  # noqa: F821
    project_memberships: Mapped[list["ProjectMember"]] = relationship("ProjectMember", back_populates="user")  # noqa: F821
    tasks_assigned: Mapped[list["Task"]] = relationship("Task", back_populates="assigned_user", foreign_keys="Task.assigned_to")  # noqa: F821
    tasks_created: Mapped[list["Task"]] = relationship("Task", back_populates="creator", foreign_keys="Task.created_by")  # noqa: F821
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="author")  # noqa: F821
    attachments: Mapped[list["Attachment"]] = relationship("Attachment", back_populates="uploader")  # noqa: F821
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="user")  # noqa: F821

    __table_args__ = (
        Index("ix_user_email", "email"),
    )
