from datetime import datetime

from bson import ObjectId
from pydantic import AliasChoices, BaseModel, Field, field_validator


class SimilarEvent(BaseModel):
    event_id: str
    similarity_score: float

    @field_validator("event_id", mode="before")
    @classmethod
    def convert_object_id_to_str(cls, value):
        if isinstance(value, ObjectId):
            return str(value)
        return value

    class Config:
        from_attributes = True


class EventSimilarity(BaseModel):
    id: str = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    event_id: str
    similar_events: list[SimilarEvent]
    last_updated: datetime

    @field_validator("id", "event_id", mode="before")
    @classmethod
    def convert_object_id_to_str(cls, value):
        if isinstance(value, ObjectId):
            return str(value)
        return value

    class Config:
        from_attributes = True
