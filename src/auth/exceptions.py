from fastapi import status

from src.auth.constants import ErrorCode
from src.exceptions import AppException


class InvalidCredentials(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Incorrect email or password"
    error_code = ErrorCode.INVALID_CREDENTIALS


class TokenExpired(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Token has expired"
    error_code = ErrorCode.TOKEN_EXPIRED


class InvalidToken(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Invalid authentication token"
    error_code = ErrorCode.INVALID_TOKEN


class SuperuserRequired(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Superuser privileges required"
    error_code = ErrorCode.FORBIDDEN_SUPERUSER
