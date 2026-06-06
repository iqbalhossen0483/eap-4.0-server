from httpx import AsyncClient


async def test_signup_valid(client: AsyncClient):
    res = await client.post("/auth/signup", json={"name": "Alice", "email": "alice@test.com", "password": "Alice1234!"})
    assert res.status_code == 201
    assert res.json()["email"] == "alice@test.com"
    assert res.json()["role"] == "team_member"


async def test_signup_duplicate_email(client: AsyncClient):
    payload = {"name": "Bob", "email": "bob@test.com", "password": "Bob12345!"}
    await client.post("/auth/signup", json=payload)
    res = await client.post("/auth/signup", json=payload)
    assert res.status_code == 409


async def test_signup_weak_password(client: AsyncClient):
    res = await client.post("/auth/signup", json={"name": "Carl", "email": "carl@test.com", "password": "weak"})
    assert res.status_code == 422


async def test_login_valid(client: AsyncClient):
    await client.post("/auth/signup", json={"name": "Dave", "email": "dave@test.com", "password": "Dave1234!"})
    res = await client.post("/auth/login", json={"email": "dave@test.com", "password": "Dave1234!"})
    assert res.status_code == 200
    assert "access_token" in res.json()


async def test_login_wrong_password(client: AsyncClient):
    await client.post("/auth/signup", json={"name": "Eve", "email": "eve@test.com", "password": "Eve12345!"})
    res = await client.post("/auth/login", json={"email": "eve@test.com", "password": "wrong"})
    assert res.status_code == 401


async def test_get_me(admin_client: AsyncClient):
    res = await admin_client.get("/auth/me")
    assert res.status_code == 200
    assert res.json()["email"] == "admin@test.com"


async def test_health(client: AsyncClient):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
