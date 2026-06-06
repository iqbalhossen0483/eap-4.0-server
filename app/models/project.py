from __future__ import annotations

import uuid
from datetime import datetime, timezone, date
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, Date, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import ProjectStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project_member import ProjectMember
    from app.models.task import Task
    from app.models.activity_log import ActivityLog


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(SAEnum(ProjectStatus), nullable=False, default=ProjectStatus.active)
    owner_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    task_count: int = 0  # populated at query time, not stored in DB

    owner: Mapped["User"] = relationship("User", back_populates="projects_owned", foreign_keys=[owner_id])  # noqa: F821
    members: Mapped[list["ProjectMember"]] = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")  # noqa: F821
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="project", cascade="all, delete-orphan")  # noqa: F821
    activity_logs: Mapped[list["ActivityLog"]] = relationship("ActivityLog", back_populates="project", cascade="all, delete-orphan")  # noqa: F821
