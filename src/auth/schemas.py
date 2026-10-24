from pydantic import EmailStr, Field

from src.auth.constants import TokenType
from src.models import CustomModel

# Auth Request & Response DTO


class LoginRequest(CustomModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RefreshTokenRequest(CustomModel):
    refresh_token: str


class TokenResponse(CustomModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(CustomModel):
    sub: str  # user id as string
    email: EmailStr
    token_type: TokenType
    exp: int
