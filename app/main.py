from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
import logging
import time

from app.utils.cloudinary_config import init_cloudinary
from app.schemas.response import ErrorResponse
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
async def request_logger(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 1)
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)"
    )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            message=exc.detail if isinstance(exc.detail, str) else "Request error",
            details=str(exc.detail),
        ).model_dump(),
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, __: IntegrityError):
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            message="A record with this value already exists",
            details="Integrity constraint violation",
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception(exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="Internal server error",
            details=str(exc),
        ).model_dump(),
    )


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
