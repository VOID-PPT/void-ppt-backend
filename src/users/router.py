from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import ActiveUserDep, SuperuserDep
from src.database import get_db
from src.pagination import PaginatedResponse, PaginationParams
from src.users import service as user_service
from src.users.dependencies import UserByIdDep
from src.users.models import User
from src.users.schemas import UserRead, UserUpdate


router = APIRouter(prefix="/users", tags=["users"])
DatabaseDep = Annotated[AsyncSession, Depends(get_db)]

# User API Router

@router.get(
    "",
    response_model=PaginatedResponse[UserRead],
    status_code=status.HTTP_200_OK,
    summary="List users",
    description="Retrieve paginated list of users. Requires authentication.",
)
async def list_users(
    session: DatabaseDep,
    _: ActiveUserDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[UserRead]:
    params = PaginationParams(page=page, page_size=page_size)
    users, total = await user_service.get_users_list(session, params)
    return PaginatedResponse.create(items=users, total=total, params=params)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get user by ID",
    description="Fetch single user details by UUID.",
)
async def get_user(
    user: UserByIdDep,
    _: ActiveUserDep,
) -> User:
    return user


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update user",
    description="Update user attributes (email, name, password, status).",
)
async def update_user(
    user: UserByIdDep,
    payload: UserUpdate,
    session: DatabaseDep,
    _: ActiveUserDep,
) -> User:
    return await user_service.update_user(session, user, payload)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete user permanently. Requires superuser privileges.",
)
async def delete_user(
    user: UserByIdDep,
    session: DatabaseDep,
    _: SuperuserDep,
) -> None:
    await user_service.delete_user(session, user)
