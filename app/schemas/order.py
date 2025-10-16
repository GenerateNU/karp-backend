from datetime import datetime
from enum import Enum

from bson import ObjectId
from pydantic import AliasChoices, BaseModel, Field, field_validator


class OrderStatus(str, Enum):
    PENDING_PICKUP = "pending pickup"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Order(BaseModel):
    id: str = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    item_id: str
    volunteer_id: str
    placed_at: datetime
    order_status: OrderStatus

    class Config:
        from_attributes = True

    @field_validator("id", "item_id", "volunteer_id", mode="before")
    @classmethod
    def convert_object_id_to_str(cls, value):
        if isinstance(value, ObjectId):
            return str(value)
        return value


class CreateOrderRequest(BaseModel):
    item_id: str


class UpdateOrderRequest(BaseModel):
    order_status: OrderStatus
