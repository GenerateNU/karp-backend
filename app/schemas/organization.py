from pydantic import BaseModel


class Organization(BaseModel):
    id: str
    name: str
    description: str
    isActive: bool = True

    class Config:
        from_attributes = True


class CreateOrganizationRequest(BaseModel):
    name: str
    description: str


class UpdateOrganizationRequest(BaseModel):
    name: str | None = None
    description: str | None = None
