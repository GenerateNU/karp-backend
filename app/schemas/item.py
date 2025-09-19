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
    expiration: datetime


class UpdateItemRequest(BaseModel):
    name: str | None = None
    price: int | None = None
    expiration: datetime | None = None
    status: str | None = None
