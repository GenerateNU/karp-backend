from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class VendorStatus(str, Enum):
    APPROVED = "APPROVED"
    IN_REVIEW = "IN_REVIEW"
    REJECTED = "REJECTED"
    DELETED = "DELETED"


class Vendor(BaseModel):
    id: str | None = None
    name: str
    business_type: str
    status: VendorStatus = VendorStatus.IN_REVIEW
    approved: bool = False
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    class Config:
        from_attributes = True


class CreateVendorRequest(BaseModel):
    name: str
    business_type: str


class UpdateVendorRequest(BaseModel):
    name: str | None = None
    business_type: str | None = None
    status: VendorStatus | None = None
