from datetime import datetime

from pydantic import BaseModel


class Vendor(BaseModel):
    name: str
    business_type: str
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    class Config:
        from_attributes = True


class CreateVendorRequest(BaseModel):
    name: str
    business_type: str
