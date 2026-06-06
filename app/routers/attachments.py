from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.attachment import Attachment
from app.models.user import User
from app.schemas.attachment import AttachmentRead
from app.schemas.response import ApiResponse, ok
from app.dependencies.auth import get_current_user
from app.services.attachment_service import upload_attachment, delete_attachment_from_cloud

router = APIRouter(tags=["attachments"])


@router.post("/tasks/{task_id}/attachments", response_model=ApiResponse[AttachmentRead], status_code=201)
async def upload(
    task_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment = await upload_attachment(file, task_id, current_user.id)
    db.add(attachment)
    await db.commit()

    attachment = (await db.execute(
        select(Attachment).options(selectinload(Attachment.uploader)).where(Attachment.id == attachment.id)
    )).scalar_one()
    return ok(AttachmentRead.model_validate(attachment), "Attachment uploaded successfully")


@router.get("/tasks/{task_id}/attachments", response_model=ApiResponse[list[AttachmentRead]])
async def list_attachments(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (await db.execute(
        select(Attachment).options(selectinload(Attachment.uploader)).where(Attachment.task_id == task_id).order_by(Attachment.created_at)
    )).scalars().all()
    return ok([AttachmentRead.model_validate(r) for r in rows], "Attachments retrieved")


@router.delete("/attachments/{attachment_id}", response_model=ApiResponse[None])
async def delete_attachment(
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment = (await db.execute(select(Attachment).where(Attachment.id == attachment_id))).scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if attachment.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own attachments")

    await delete_attachment_from_cloud(attachment)
    await db.delete(attachment)
    await db.commit()
    return ok(None, "Attachment deleted successfully")
