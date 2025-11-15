from datetime import datetime
from enum import Enum

from bson import ObjectId
from pydantic import AliasChoices, BaseModel, Field, field_validator


class ItemStatus(str, Enum):
    APPROVED = "APPROVED"
    IN_REVIEW = "IN_REVIEW"
    REJECTED = "REJECTED"
    DELETED = "DELETED"
    ACTIVE = "ACTIVE"
    CLAIMED = "CLAIMED"


class Item(BaseModel):
    id: str = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    name: str
    status: ItemStatus
    vendor_id: str
    time_posted: datetime = datetime.now()
    expiration: datetime
    price: int
    tags: list[str] = []
    description: str | None = None
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
    description: str | None = None
    tags: list[str] | None = None
    image_s3_key: str | None = None


class UpdateItemRequest(BaseModel):
    name: str | None = None
    price: int | None = None
    expiration: datetime | None = None
    status: ItemStatus | None = None
