# Smart Project & Task Collaboration System

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Cloudinary account (free tier works)

---

## Backend

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env` and fill in your values:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
SECRET_KEY=your-random-secret-here
ACCESS_TOKEN_EXPIRE_MINUTES=60
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

### 3. Create the database

```bash
# In psql or your DB tool
CREATE DATABASE dbname;
```

### 4. Run migrations

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 5. Seed demo data

```bash
python -m app.utils.seed
```

Demo credentials:

| Email            | Password     | Role            |
| ---------------- | ------------ | --------------- |
| admin@demo.com   | Admin1234!   | Admin           |
| manager@demo.com | Manager1234! | Project Manager |
| member@demo.com  | Member1234!  | Team Member     |

### 6. Start the server

```bash
uvicorn app.main:app --reload
```

API runs at `http://localhost:8000`
Interactive docs at `http://localhost:8000/docs`

---

## Running tests (backend)

Then run:

```bash
pytest
```
