from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.comment import Comment
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentRead
from app.dependencies.auth import get_current_user
from app.utils.activity_logger import log_activity

router = APIRouter(tags=["comments"])


@router.get("/tasks/{task_id}/comments", response_model=list[CommentRead])
async def list_comments(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (await db.execute(
        select(Comment).options(selectinload(Comment.author)).where(Comment.task_id == task_id).order_by(Comment.created_at)
    )).scalars().all()
    return rows


@router.post("/tasks/{task_id}/comments", response_model=CommentRead, status_code=201)
async def add_comment(
    task_id: str,
    body: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = Comment(task_id=task_id, author_id=current_user.id, body=body.body)
    db.add(comment)
    await db.flush()
    await log_activity(db, current_user, "comment.added", "Comment", comment.id, None, {"task_id": task_id})
    await db.commit()

    return (await db.execute(
        select(Comment).options(selectinload(Comment.author)).where(Comment.id == comment.id)
    )).scalar_one()


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = (await db.execute(select(Comment).where(Comment.id == comment_id))).scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own comments")
    await db.delete(comment)
    await db.commit()
