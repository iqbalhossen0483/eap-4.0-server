import enum


class Role(str, enum.Enum):
    admin = "admin"
    project_manager = "project_manager"
    team_member = "team_member"


class ProjectStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    on_hold = "on_hold"


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    completed = "completed"


class Priority(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"
