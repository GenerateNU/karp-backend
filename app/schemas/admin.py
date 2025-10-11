from enum import Enum

from pydantic import BaseModel

from .user import User


class Status(str, Enum):
    APPROVED = "APPROVED"
    IN_REVIEW = "IN_REVIEW"
    REJECTED = "REJECTED"
    DELETED = "DELETED"


class Admin(User):
    # inherits everything from Membership
    id: str
    is_active: bool

    class Config:
        from_attributes = True


class AdminResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    username: str

    class Config:
        from_attributes = True


class CreateAdminRequest(BaseModel):
    username: str
    email: str
    password: str
    first_name: str
    last_name: str


class UpdateOrganizationRequest(BaseModel):
    organization_id: str
    status: str


class UpdateVendorRequest(BaseModel):
    vendor_id: str
    status: str


class UpdateItemRequest(BaseModel):
    item_id: str
    status: str


class UpdateEventRequest(BaseModel):
    event_id: str
    status: str
