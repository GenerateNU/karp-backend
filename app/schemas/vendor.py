from datetime import datetime
from enum import Enum

from bson import ObjectId
from pydantic import AliasChoices, BaseModel, Field, field_validator

from app.schemas.location import Location


class VendorStatus(str, Enum):
    APPROVED = "APPROVED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    DELETED = "DELETED"


class Vendor(BaseModel):
    id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    name: str
    business_type: str
    status: VendorStatus = VendorStatus.PENDING
    location: Location | None = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    website: str | None = None
    address: str | None = None

    class Config:
        from_attributes = True

    @field_validator("id", mode="before")
    @classmethod
    def convert_object_id_to_str(cls, value):
        if isinstance(value, ObjectId):
            return str(value)
        return value


class CreateVendorRequest(BaseModel):
    name: str
    business_type: str
    address: str | None = None
    website: str | None = None


class UpdateVendorRequest(BaseModel):
    name: str | None = None
    business_type: str | None = None
    status: VendorStatus | None = None
    address: str | None = None
    website: str | None = None
