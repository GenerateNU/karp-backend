from datetime import datetime

from pydantic import BaseModel


class Item(BaseModel):
    name: str
    status: str
    timePosted: datetime = datetime.now()
    expiration: datetime
    price: str

    class Config:
        from_attributes = True


class CreateItemRequest(BaseModel):
    name: str
    expiration: str


class UpdateItemRequest(BaseModel):
    name: str | None
    price: int | None
    expiration: str | None
    status: str | None
