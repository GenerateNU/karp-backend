from datetime import datetime
from enum import Enum

from bson import ObjectId
from pydantic import AliasChoices, BaseModel, Field, field_validator


class ItemStatus(str, Enum):
    PUBLISHED = "PUBLISHED"
    DELETED = "DELETED"
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ACTIVE = "ACTIVE"


class Item(BaseModel):
    id: str = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    name: str
    status: ItemStatus
    vendor_id: str
    time_posted: datetime = datetime.now()
    expiration: datetime
    price: int
    image_s3_key: str | None = None

    @field_validator("id", "vendor_id", mode="before")
    @classmethod
    def convert_object_id_to_str(cls, value):
        if isinstance(value, ObjectId):
            return str(value)
        return value

    class Config:
        from_attributes = True


class ItemSortParam(str, Enum):
    DATE = "date"
    NAME = "name"
    COINS = "coins"
    CREATED_AT = "created_at"

    @property
    def field_name(self) -> str:
        field_mapping = {
            ItemSortParam.DATE: "time_posted",
            ItemSortParam.NAME: "name",
            ItemSortParam.COINS: "price",
            ItemSortParam.CREATED_AT: "created_at",
        }
        return field_mapping[self]


class CreateItemRequest(BaseModel):
    name: str
    expiration: datetime


class UpdateItemRequest(BaseModel):
    name: str | None = None
    price: int | None = None
    expiration: datetime | None = None
    status: ItemStatus | None = None
