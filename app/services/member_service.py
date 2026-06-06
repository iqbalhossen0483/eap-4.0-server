from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User


async def list_members(
    db: AsyncSession, project_id: str, current_user: User
) -> list[ProjectMember]:
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    rows = (
        (
            await db.execute(
                select(ProjectMember)
                .options(selectinload(ProjectMember.user))
                .where(ProjectMember.project_id == project_id)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def add_member(
    db: AsyncSession, project_id: str, user_id: str, current_user: User
) -> ProjectMember:
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = (
        await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409, detail="User is already a member of this project"
        )

    member = ProjectMember(project_id=project_id, user_id=user_id)
    db.add(member)
    await db.commit()
    await db.refresh(member)

    # Eager load user for response
    result = (
        await db.execute(
            select(ProjectMember)
            .options(selectinload(ProjectMember.user))
            .where(
                ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
            )
        )
    ).scalar_one()
    return result


async def remove_member(
    db: AsyncSession, project_id: str, user_id: str, current_user: User
) -> None:
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove the project owner")

    member = (
        await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    await db.delete(member)
    await db.commit()
