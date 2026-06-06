from sqlalchemy.ext.asyncio import AsyncSession
from app.models.activity_log import ActivityLog
from app.models.user import User


async def log_activity(
    db: AsyncSession,
    actor: User,
    action: str,
    entity_type: str,
    entity_id: str,
    project_id: str | None = None,
    detail: dict | None = None,
) -> None:
    entry = ActivityLog(
        actor_id=actor.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        detail=detail or {},
    )
    db.add(entry)
    # Caller is responsible for committing — do not commit here
