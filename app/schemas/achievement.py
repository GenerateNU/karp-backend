from bson import ObjectId
from pydantic import AliasChoices, BaseModel, Field, field_validator


class Achievement(BaseModel):
    id: str = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    name: str
    description: str
    level: int
    is_active: bool
    # [How to store fish TBD]

    @field_validator("id", mode="before")
    @classmethod
    def convert_object_id_to_str(cls, value):
        if isinstance(value, ObjectId):
            return str(value)
        return value

    class Config:
        from_attributes = True


class CreateAchievementRequest(BaseModel):
    name: str
    description: str
    level: int
    is_active: bool = True


class UpdateAchievementRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    level: int | None = None
