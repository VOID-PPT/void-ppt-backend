from enum import StrEnum


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class ErrorCode(StrEnum):
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    FORBIDDEN_SUPERUSER = "FORBIDDEN_SUPERUSER"
