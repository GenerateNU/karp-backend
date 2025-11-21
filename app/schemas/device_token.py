from bson import ObjectId
from pydantic import AliasChoices, BaseModel, Field, field_validator


class CreateDeviceTokenRequest(BaseModel):
    device_token: str


class UnregisterDeviceTokenRequest(BaseModel):
    volunteer_id: str


class DeviceToken(BaseModel):
    id: str = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    device_token: str
    volunteer_id: str

    @field_validator("id", mode="before")
    @classmethod
    def convert_object_id_to_str(cls, value):
        if isinstance(value, ObjectId):
            return str(value)
        return value

    class Config:
        from_attributes = True
