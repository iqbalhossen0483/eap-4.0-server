from datetime import date, timedelta
from httpx import AsyncClient


def future_date(days=30):
    return str(date.today() + timedelta(days=days))


async def test_create_project_as_pm(pm_client: AsyncClient):
    res = await pm_client.post("/projects", json={"name": "Test Project", "deadline": future_date(), "status": "active"})
    assert res.status_code == 201
    assert res.json()["name"] == "Test Project"


async def test_create_project_as_member_forbidden(member_client: AsyncClient):
    res = await member_client.post("/projects", json={"name": "Forbidden", "deadline": future_date(), "status": "active"})
    assert res.status_code == 403


async def test_list_projects(pm_client: AsyncClient):
    await pm_client.post("/projects", json={"name": "Project A", "deadline": future_date(), "status": "active"})
    res = await pm_client.get("/projects")
    assert res.status_code == 200
    assert res.json()["total"] >= 1


async def test_project_cascade_delete(pm_client: AsyncClient):
    res = await pm_client.post("/projects", json={"name": "To Delete", "deadline": future_date()})
    project_id = res.json()["id"]
    del_res = await pm_client.delete(f"/projects/{project_id}")
    assert del_res.status_code == 204
    get_res = await pm_client.get(f"/projects/{project_id}")
    assert get_res.status_code == 404
