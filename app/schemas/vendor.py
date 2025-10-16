from datetime import datetime
from enum import Enum

from bson import ObjectId
from pydantic import AliasChoices, BaseModel, Field, field_validator


class VendorStatus(str, Enum):
    APPROVED = "APPROVED"
    IN_REVIEW = "IN_REVIEW"
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
    status: VendorStatus = VendorStatus.IN_REVIEW
    approved: bool = False
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

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


class UpdateVendorRequest(BaseModel):
    name: str | None = None
    business_type: str | None = None
    status: VendorStatus | None = None
