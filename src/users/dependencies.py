import uuid
from typing import Annotated

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.users import service as user_service
from src.users.exceptions import UserNotFound
from src.users.models import User

DatabaseDep = Annotated[AsyncSession, Depends(get_db)]


async def valid_user_id(
    user_id: Annotated[uuid.UUID, Path(description="The UUID of the user")],
    session: DatabaseDep,
) -> User:
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise UserNotFound()
    return user


UserByIdDep = Annotated[User, Depends(valid_user_id)]
