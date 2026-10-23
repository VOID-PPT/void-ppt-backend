import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import service as auth_service
from src.pagination import PaginationParams
from src.users.exceptions import EmailAlreadyExists
from src.users.models import User
from src.users.schemas import UserCreate, UserUpdate

# User Service

async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_users_list(
    session: AsyncSession,
    pagination: PaginationParams,
) -> tuple[Sequence[User], int]:
    count_stmt = select(func.count(User.id))
    total_count = (await session.execute(count_stmt)).scalar() or 0

    stmt = (
        select(User)
        .order_by(User.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    result = await session.execute(stmt)
    users = result.scalars().all()
    return users, total_count


async def create_user(session: AsyncSession, data: UserCreate) -> User:
    existing = await get_user_by_email(session, data.email)
    if existing:
        raise EmailAlreadyExists()

    user = User(
        email=data.email,
        hashed_password=auth_service.hash_password(data.password),
        full_name=data.full_name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(
    session: AsyncSession,
    user: User,
    data: UserUpdate,
) -> User:
    if data.email is not None and data.email != user.email:
        existing = await get_user_by_email(session, data.email)
        if existing:
            raise EmailAlreadyExists()
        user.email = data.email

    if data.full_name is not None:
        user.full_name = data.full_name

    if data.is_active is not None:
        user.is_active = data.is_active

    if data.password is not None:
        user.hashed_password = auth_service.hash_password(data.password)

    await session.commit()
    await session.refresh(user)
    return user


async def delete_user(session: AsyncSession, user: User) -> None:
    await session.delete(user)
    await session.commit()
