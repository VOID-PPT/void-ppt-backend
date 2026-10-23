import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from src.models import CustomModel

# User Request & Response DTO

class UserBase(CustomModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool = True


class UserCreate(CustomModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserUpdate(CustomModel):
    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_active: bool | None = None


class UserRead(UserBase):
    id: uuid.UUID
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
