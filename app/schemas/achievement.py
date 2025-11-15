from datetime import datetime

from bson import ObjectId
from pydantic import AliasChoices, BaseModel, Field, field_validator

from app.schemas.karp_event import KarpEvent


class Achievement(BaseModel):
    id: str = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    name: str
    description: str
    event_type: KarpEvent
    threshold: int
    image_s3_key: str | None = None
    is_active: bool

    @field_validator("id", mode="before")
    @classmethod
    def convert_object_id_to_str(cls, value):
        if isinstance(value, ObjectId):
            return str(value)
        return value

    class Config:
        from_attributes = True


class VolunteerReceivedAchievementResponse(Achievement):
    received_at: datetime


class CreateAchievementRequest(BaseModel):
    name: str
    description: str
    event_type: KarpEvent
    threshold: int
    is_active: bool = True


class UpdateAchievementRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    event_type: KarpEvent | None = None
    threshold: int | None = None
