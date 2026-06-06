from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationRead, UnreadCountResponse
from app.schemas.response import ApiResponse, ok, ok_paginated
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=ApiResponse[list[NotificationRead]])
async def list_notifications(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.created_at.desc())
    total: int = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    rows = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return ok_paginated(
        [NotificationRead.model_validate(r) for r in rows], total, page, page_size, "Notifications retrieved"
    )


@router.get("/unread-count", response_model=ApiResponse[UnreadCountResponse])
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = (await db.execute(
        select(func.count(Notification.id)).where(Notification.user_id == current_user.id, Notification.is_read == False)  # noqa: E712
    )).scalar() or 0
    return ok(UnreadCountResponse(count=count), "Unread count retrieved")


@router.patch("/read-all", response_model=ApiResponse[None])
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (await db.execute(
        select(Notification).where(Notification.user_id == current_user.id, Notification.is_read == False)  # noqa: E712
    )).scalars().all()
    for n in rows:
        n.is_read = True
    await db.commit()
    return ok(None, "All notifications marked as read")


@router.patch("/{notification_id}/read", response_model=ApiResponse[NotificationRead])
async def mark_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = (await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == current_user.id)
    )).scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    await db.commit()
    await db.refresh(notif)
    return ok(NotificationRead.model_validate(notif), "Notification marked as read")


@router.delete("/{notification_id}", response_model=ApiResponse[None])
async def delete_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = (await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == current_user.id)
    )).scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.delete(notif)
    await db.commit()
    return ok(None, "Notification deleted successfully")
