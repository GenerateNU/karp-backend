from datetime import datetime

from pydantic import BaseModel


class Item(BaseModel):
    name: str
    status: str
    timePosted: datetime = datetime.now()
    expiration: datetime
    price: int

    class Config:
        from_attributes = True


class CreateItemRequest(BaseModel):
    name: str
    expiration: str  # should be in DD-MM-YYYY H:M:S format


class UpdateItemRequest(BaseModel):
    name: str | None = None
    price: int | None = None
    expiration: str | None = None
    status: str | None = None
