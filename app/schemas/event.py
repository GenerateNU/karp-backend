from datetime import UTC, datetime

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.data_types import EventType, Location, Status


class Event(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    name: str
    address: str
    location: Location | None = None
    start_date_time: datetime
    end_date_time: datetime
    organization_id: str
    status: Status
    max_volunteers: int
    coins: int
    tags: list[EventType] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str

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
    address: str
    start_date_time: datetime
    end_date_time: datetime
    max_volunteers: int
    coins: int
    tags: list[EventType] = Field(default_factory=list)


class UpdateEventStatusRequest(BaseModel):
    status: Status | None = None
    name: str | None = None
    location: str | None = None
    max_volunteers: int | None = None
    start_date_time: datetime | None = None
    end_date_time: datetime | None = None
    coins: int | None = None
    tags: list[EventType] | None = None

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)
