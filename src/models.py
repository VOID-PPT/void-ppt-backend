from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, field_serializer
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Consistent naming convention for PostgreSQL constraints and indexes
POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)


class CustomModel(BaseModel):
    """Custom base model enforcing ISO-8601 UTC datetimes and attribute mapping."""

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    @field_serializer("*", when_used="json", check_fields=False)
    def _serialize_datetimes(self, value: object) -> object:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=ZoneInfo("UTC"))
            return value.strftime("%Y-%m-%dT%H:%M:%S%z")
        return value
