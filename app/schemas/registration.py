from datetime import datetime
from enum import Enum

from bson import ObjectId
from pydantic import AliasChoices, BaseModel, Field, field_validator


class RegistrationStatus(str, Enum):
    UPCOMING = "upcoming"
    COMPLETED = "completed"
    INCOMPLETED = "incompleted"
    UNREGISTERED = "unregistered"


class Registration(BaseModel):
    id: str = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    event_id: str
    volunteer_id: str
    registered_at: datetime
    registration_status: RegistrationStatus
    clocked_in: datetime | None
    clocked_out: datetime | None

    class Config:
        from_attributes = True

    @field_validator("id", "event_id", "volunteer_id", mode="before")
    @classmethod
    def convert_object_id_to_str(cls, value):
        if isinstance(value, ObjectId):
            return str(value)
        return value


class CreateRegistrationRequest(BaseModel):
    event_id: str
