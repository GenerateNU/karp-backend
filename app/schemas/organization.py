from enum import Enum

from bson import ObjectId
from pydantic import AliasChoices, BaseModel, Field, field_validator

from app.schemas.location import Location


class OrganizationStatus(str, Enum):
    APPROVED = "APPROVED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    DELETED = "DELETED"


class Organization(BaseModel):
    id: str = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    name: str
    description: str
    status: OrganizationStatus
    location: Location | None = None
    image_s3_key: str | None = None

    class Config:
        from_attributes = True

    @field_validator("id", mode="before")
    @classmethod
    def convert_object_id_to_str(cls, value):
        if isinstance(value, ObjectId):
            return str(value)
        return value


class CreateOrganizationRequest(BaseModel):
    name: str
    description: str
    address: str


class UpdateOrganizationRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: OrganizationStatus | None = None
    address: str | None = None
