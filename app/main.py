from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
import time
import logging

from app.utils.cloudinary_config import init_cloudinary
from app.routers import (
    auth,
    users,
    projects,
    tasks,
    comments,
    attachments,
    dashboard,
    activity,
    notifications,
    search,
)

logger = logging.getLogger("app.access")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_cloudinary()
    yield


app = FastAPI(
    title="Smart Project & Task Collaboration System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logger(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 1)
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)"
    )
    return response


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request, exc):
    return JSONResponse(
        status_code=409, content={"detail": "A record with this value already exists"}
    )


@app.exception_handler(Exception)
async def generic_error_handler(request, exc):
    logger.exception(exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(comments.router)
app.include_router(attachments.router)
app.include_router(dashboard.router)
app.include_router(activity.router)
app.include_router(notifications.router)
app.include_router(search.router)
