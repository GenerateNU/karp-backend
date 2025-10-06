from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class Item(BaseModel):
    id: str
    name: str
    status: str
    vendor_id: str
    time_posted: datetime = datetime.now()
    expiration: datetime
    price: int

    class Config:
        from_attributes = True


class ItemSortParam(str, Enum):
    DATE = "date"
    NAME = "name"
    COINS = "coins"

    @property
    def field_name(self) -> str:
        field_mapping = {
            ItemSortParam.DATE: "time_posted",
            ItemSortParam.NAME: "name",
            ItemSortParam.COINS: "price",
        }
        return field_mapping[self]


class CreateItemRequest(BaseModel):
    name: str
    expiration: datetime


class UpdateItemRequest(BaseModel):
    name: str | None = None
    price: int | None = None
    expiration: datetime | None = None
    status: str | None = None
