import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import service as auth_service
from src.auth.constants import TokenType
from src.auth.exceptions import InvalidToken, SuperuserRequired
from src.database import get_db
from src.users import service as user_service
from src.users.exceptions import UserInactive, UserNotFound
from src.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

DatabaseDep = Annotated[AsyncSession, Depends(get_db)]
TokenDep = Annotated[str | None, Depends(oauth2_scheme)]


async def get_current_user(
    session: DatabaseDep,
    token: TokenDep,
) -> User:
    if not token:
        raise InvalidToken(detail="Not authenticated")

    token_data = auth_service.decode_token(token, expected_type=TokenType.ACCESS)
    try:
        user_uuid = uuid.UUID(token_data.sub)
    except ValueError as err:
        raise InvalidToken(detail="Invalid user ID format in token") from err

    user = await user_service.get_user_by_id(session, user_uuid)
    if not user:
        raise UserNotFound()

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_current_active_user(user: CurrentUserDep) -> User:
    if not user.is_active:
        raise UserInactive()
    return user


ActiveUserDep = Annotated[User, Depends(get_current_active_user)]


async def get_current_superuser(user: ActiveUserDep) -> User:
    if not user.is_superuser:
        raise SuperuserRequired()
    return user


SuperuserDep = Annotated[User, Depends(get_current_superuser)]
