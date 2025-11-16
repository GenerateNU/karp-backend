from datetime import UTC, datetime

from bson import ObjectId
from pydantic import AliasChoices, BaseModel, Field, field_validator


class VolunteerAchievement(BaseModel):
    id: str = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    achievement_id: str
    volunteer_id: str
    received_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

    @field_validator("id", "achievement_id", "volunteer_id", mode="before")
    @classmethod
    def convert_object_id_to_str(cls, value):
        if isinstance(value, ObjectId):
            return str(value)
        return value


class CreateVolunteerAchievementRequest(BaseModel):
    achievement_id: str
    volunteer_id: str
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
