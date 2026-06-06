from __future__ import annotations

import math
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    total: int
    current_page: int
    total_page: int


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: T | None = None
    meta: PaginationMeta | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    details: str | None = None


def ok(data: T, message: str = "Success") -> ApiResponse[T]:
    return ApiResponse(success=True, message=message, data=data)


def ok_paginated(
    data: list[Any],
    total: int,
    page: int,
    page_size: int,
    message: str = "Success",
) -> ApiResponse[list[Any]]:
    return ApiResponse(
        success=True,
        message=message,
        data=data,
        meta=PaginationMeta(
            total=total,
            current_page=page,
            total_page=math.ceil(total / page_size) if total else 0,
        ),
    )
