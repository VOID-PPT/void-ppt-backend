from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import Field

from src.models import CustomModel

T = TypeVar("T")

# Pagination Management

class PaginationParams(CustomModel):
    page: int = Field(default=1, ge=1, description="Page number, starting from 1")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(CustomModel, Generic[T]):
    items: Sequence[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(
        cls,
        items: Sequence[T],
        total: int,
        params: PaginationParams,
    ) -> "PaginatedResponse[T]":
        pages = (total + params.page_size - 1) // params.page_size if params.page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            pages=pages,
        )
