import asyncio
from datetime import date, timedelta
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.enums import Role, ProjectStatus, TaskStatus, Priority
from app.utils.security import _hash


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # --- Users ---
        users_data = [
            {"email": "admin@demo.com", "name": "Admin User", "password": "Admin1234!", "role": Role.admin},
            {"email": "manager@demo.com", "name": "Project Manager", "password": "Manager1234!", "role": Role.project_manager},
            {"email": "member@demo.com", "name": "Team Member", "password": "Member1234!", "role": Role.team_member},
        ]
        created_users: dict[str, User] = {}
        for u in users_data:
            existing = (await db.execute(select(User).where(User.email == u["email"]))).scalar_one_or_none()
            if not existing:
                user = User(
                    name=u["name"],
                    email=u["email"],
                    hashed_password=_hash(u["password"]),
                    role=u["role"],
                    is_active=True,
                )
                db.add(user)
                await db.flush()
                created_users[u["email"]] = user
            else:
                created_users[u["email"]] = existing

        manager = created_users["manager@demo.com"]
        member = created_users["member@demo.com"]

        # --- Projects ---
        projects_data = [
            {"name": "E-Commerce App", "description": "Full-stack e-commerce platform", "deadline": date.today() + timedelta(days=30), "status": ProjectStatus.active},
            {"name": "Mobile Dashboard", "description": "Analytics dashboard for mobile", "deadline": date.today() + timedelta(days=14), "status": ProjectStatus.active},
            {"name": "Admin Panel", "description": "Internal admin tooling", "deadline": date.today() + timedelta(days=60), "status": ProjectStatus.on_hold},
        ]
        created_projects: list[Project] = []
        for p in projects_data:
            existing = (await db.execute(select(Project).where(Project.name == p["name"]))).scalar_one_or_none()
            if not existing:
                project = Project(owner_id=manager.id, **p)
                db.add(project)
                await db.flush()
                # Add manager and member as members
                db.add(ProjectMember(project_id=project.id, user_id=manager.id))
                db.add(ProjectMember(project_id=project.id, user_id=member.id))
                created_projects.append(project)
            else:
                created_projects.append(existing)

        # --- Tasks (only if first project was just created) ---
        if created_projects:
            proj = created_projects[0]
            tasks_data = [
                {"title": "Setup API", "due_date": date.today() + timedelta(days=7), "priority": Priority.high, "status": TaskStatus.in_progress, "assigned_to": member.id},
                {"title": "Design Homepage", "due_date": date.today() + timedelta(days=10), "priority": Priority.medium, "status": TaskStatus.todo, "assigned_to": member.id},
                {"title": "Write Tests", "due_date": date.today() + timedelta(days=20), "priority": Priority.low, "status": TaskStatus.todo, "assigned_to": None},
            ]
            for t in tasks_data:
                existing = (await db.execute(select(Task).where(Task.title == t["title"], Task.project_id == proj.id))).scalar_one_or_none()
                if not existing:
                    db.add(Task(project_id=proj.id, created_by=manager.id, **t))

        await db.commit()
        print("Seed completed successfully.")
        print("  admin@demo.com    / Admin1234!")
        print("  manager@demo.com  / Manager1234!")
        print("  member@demo.com   / Member1234!")


if __name__ == "__main__":
    asyncio.run(seed())
