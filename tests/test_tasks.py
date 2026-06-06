from datetime import date, timedelta
from httpx import AsyncClient


def future_date(days=10):
    return str(date.today() + timedelta(days=days))


def past_date():
    return str(date.today() - timedelta(days=1))


async def _create_project(client: AsyncClient, name="Test Project") -> str:
    res = await client.post("/projects", json={"name": name, "deadline": future_date(30), "status": "active"})
    assert res.status_code == 201
    return res.json()["id"]


async def test_create_task_valid(pm_client: AsyncClient):
    pid = await _create_project(pm_client)
    res = await pm_client.post(f"/projects/{pid}/tasks", json={"title": "Task 1", "due_date": future_date(), "priority": "high"})
    assert res.status_code == 201
    assert res.json()["title"] == "Task 1"


async def test_create_task_duplicate_title(pm_client: AsyncClient):
    pid = await _create_project(pm_client)
    payload = {"title": "Dup Task", "due_date": future_date(), "priority": "medium"}
    await pm_client.post(f"/projects/{pid}/tasks", json=payload)
    res = await pm_client.post(f"/projects/{pid}/tasks", json=payload)
    assert res.status_code == 409


async def test_create_task_past_due_date(pm_client: AsyncClient):
    pid = await _create_project(pm_client)
    res = await pm_client.post(f"/projects/{pid}/tasks", json={"title": "Past Task", "due_date": past_date(), "priority": "low"})
    assert res.status_code == 422


async def test_update_task_status(pm_client: AsyncClient):
    pid = await _create_project(pm_client)
    task_res = await pm_client.post(f"/projects/{pid}/tasks", json={"title": "Status Task", "due_date": future_date(), "priority": "low"})
    task_id = task_res.json()["id"]
    res = await pm_client.patch(f"/tasks/{task_id}/status", json={"status": "in_progress"})
    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"
