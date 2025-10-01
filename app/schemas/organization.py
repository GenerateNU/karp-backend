from enum import Enum

from pydantic import BaseModel


class Status(str, Enum):
    APPROVED = "APPROVED"
    IN_REVIEW = "IN_REVIEW"
    REJECTED = "REJECTED"
    DELETED = "DELETED"


class Organization(BaseModel):
    id: str
    name: str
    description: str
    status: Status

    class Config:
        from_attributes = True


class CreateOrganizationRequest(BaseModel):
    name: str
    description: str


class UpdateOrganizationRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: Status | None = None
