import uuid
from datetime import datetime, timezone, date
from sqlalchemy import String, Text, Date, DateTime, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import TaskStatus, Priority


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    priority: Mapped[Priority] = mapped_column(SAEnum(Priority), nullable=False, default=Priority.medium)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), nullable=False, default=TaskStatus.todo)
    created_by: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project: Mapped["Project"] = relationship("Project", back_populates="tasks")  # noqa: F821
    assigned_user: Mapped["User | None"] = relationship("User", back_populates="tasks_assigned", foreign_keys=[assigned_to])  # noqa: F821
    creator: Mapped["User"] = relationship("User", back_populates="tasks_created", foreign_keys=[created_by])  # noqa: F821
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="task", cascade="all, delete-orphan")  # noqa: F821
    attachments: Mapped[list["Attachment"]] = relationship("Attachment", back_populates="task", cascade="all, delete-orphan")  # noqa: F821

    __table_args__ = (
        Index("ix_task_project_id", "project_id"),
        Index("ix_task_assigned_to", "assigned_to"),
        Index("ix_task_due_date", "due_date"),
        Index("ix_task_priority", "priority"),
        Index("ix_task_status", "status"),
    )
