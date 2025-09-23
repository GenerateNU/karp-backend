from datetime import UTC, datetime
from enum import Enum

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Status(str, Enum):
    PUBLISHED = "published"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DRAFT = "draft"
    DELETED = "deleted"


class Event(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    name: str
    location: str
    start_date_time: datetime
    end_date_time: datetime
    organization_id: str
    status: Status
    max_volunteers: int
    coins: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(
        use_enum_values=True,
        from_attributes=True,
        populate_by_name=True,
        extra="ignore",
    )

    @model_validator(mode="before")
    def _convert_objectid(cls, data: dict):
        if data and "_id" in data and isinstance(data["_id"], ObjectId):
            data["_id"] = str(data["_id"])
        return data


class CreateEventRequest(BaseModel):
    name: str
    location: str
    start_date_time: datetime
    end_date_time: datetime
    organization_id: str
    max_volunteers: int
    coins: int


class UpdateEventStatusRequestDTO(BaseModel):
    status: Status
    name: str
    location: str
    max_volunteers: int
    start_date_time: datetime
    end_date_time: datetime
    coins: int

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)
