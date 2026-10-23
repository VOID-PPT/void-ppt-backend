from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "Internal server error"
    error_code: str = "INTERNAL_ERROR"
    extra: dict[str, Any] | None = None

    def __init__(
        self,
        detail: str | None = None,
        status_code: int | None = None,
        error_code: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.extra = extra
        super().__init__(self.detail)


class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found"
    error_code = "NOT_FOUND"


class BadRequestException(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Bad request"
    error_code = "BAD_REQUEST"


class UnauthorizedException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Not authenticated"
    error_code = "UNAUTHORIZED"


class ForbiddenException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Forbidden access"
    error_code = "FORBIDDEN"


class ConflictException(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource conflict"
    error_code = "CONFLICT"


async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    content: dict[str, Any] = {
        "detail": exc.detail,
        "error_code": exc.error_code,
    }
    if exc.extra:
        content["extra"] = exc.extra
    return JSONResponse(status_code=exc.status_code, content=content)
