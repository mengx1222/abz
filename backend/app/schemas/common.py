from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """统一成功响应格式。"""
    success: bool = True
    data: T
    request_id: str | None = None


class ErrorDetail(BaseModel):
    """错误详情。"""
    code: str
    message: str


class ErrorResponse(BaseModel):
    """统一错误响应格式。"""
    success: bool = False
    error: ErrorDetail
    request_id: str | None = None


class PaginationMeta(BaseModel):
    """分页元信息。"""
    page: int = Field(ge=1, description="当前页码")
    page_size: int = Field(ge=1, le=100, description="每页条数")
    total: int = Field(ge=0, description="总条数")
    total_pages: int = Field(ge=0, description="总页数")


class PaginatedResponse(BaseModel, Generic[T]):
    """带分页的成功响应。"""
    success: bool = True
    data: list[T]
    pagination: PaginationMeta
    request_id: str | None = None

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
        request_id: str | None = None,
    ) -> "PaginatedResponse[T]":
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            data=items,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
            ),
            request_id=request_id,
        )
