from enum import Enum

from pydantic import BaseModel, Field


class Status(str, Enum):
    APPROVED = "APPROVED"
    IN_REVIEW = "IN_REVIEW"
    REJECTED = "REJECTED"
    DELETED = "DELETED"


class OrgApplicationID(BaseModel):
    id: str
    organization_id: str
    status: Status


class VendorApplicationID(BaseModel):
    id: str
    vendor_id: str
    status: Status


class Admin(BaseModel):
    first_name: str
    last_name: str
    org_applications: list[OrgApplicationID] = Field(default_factory=list)
    vendor_applications: list[VendorApplicationID] = Field(default_factory=list)

    class Config:
        from_attributes = True


class CreateAdminRequest(BaseModel):
    first_name: str
    last_name: str
    org_applications: list[OrgApplicationID] = Field(default_factory=list)
    vendor_applications: list[VendorApplicationID] = Field(default_factory=list)


class ApproveOrganizationRequest(BaseModel):
    organization_id: str
    status: str


class ApproveVendorRequest(BaseModel):
    vendor_id: str
    status: str


class ApproveItemRequest(BaseModel):
    item_id: str
    status: str


class ApproveEventRequest(BaseModel):
    event_id: str
    status: str
