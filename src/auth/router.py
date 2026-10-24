import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import service as auth_service
from src.auth.constants import TokenType
from src.auth.dependencies import ActiveUserDep
from src.auth.exceptions import InvalidCredentials, InvalidToken
from src.auth.schemas import LoginRequest, RefreshTokenRequest, TokenResponse
from src.database import get_db
from src.users import service as user_service
from src.users.models import User
from src.users.schemas import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])
DatabaseDep = Annotated[AsyncSession, Depends(get_db)]

# Auth Api Router


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new standard user account with email and password.",
)
async def register(
    payload: UserCreate,
    session: DatabaseDep,
) -> User:
    return await user_service.create_user(session, payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login to obtain tokens",
    description="Authenticates user credentials and returns JWT access and refresh tokens.",
)
async def login(
    payload: LoginRequest,
    session: DatabaseDep,
) -> TokenResponse:
    user = await user_service.get_user_by_email(session, payload.email)
    if not user or not auth_service.verify_password(payload.password, user.hashed_password):
        raise InvalidCredentials()
    if not user.is_active:
        raise InvalidCredentials(detail="Account is inactive")

    return auth_service.create_auth_tokens(user.id, user.email)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Exchanges a valid refresh token for a fresh token pair.",
)
async def refresh_token(
    payload: RefreshTokenRequest,
    session: DatabaseDep,
) -> TokenResponse:
    token_data = auth_service.decode_token(payload.refresh_token, expected_type=TokenType.REFRESH)
    try:
        user_uuid = uuid.UUID(token_data.sub)
    except ValueError as err:
        raise InvalidToken(detail="Invalid user ID format in token") from err

    user = await user_service.get_user_by_id(session, user_uuid)
    if not user or not user.is_active:
        raise InvalidCredentials(detail="User no longer active or exists")

    return auth_service.create_auth_tokens(user.id, user.email)


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Fetches profile information of the currently authenticated user.",
)
async def get_current_user_profile(
    current_user: ActiveUserDep,
) -> User:
    return current_user
