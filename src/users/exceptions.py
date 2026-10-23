from fastapi import status

from src.exceptions import AppException
from src.users.constants import ErrorCode


class UserNotFound(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "User not found"
    error_code = ErrorCode.USER_NOT_FOUND


class EmailAlreadyExists(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Email is already registered"
    error_code = ErrorCode.EMAIL_ALREADY_EXISTS


class UserInactive(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "User account is inactive"
    error_code = ErrorCode.USER_INACTIVE
