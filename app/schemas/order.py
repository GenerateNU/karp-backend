from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class OrderStatus(str, Enum):
    PENDING_PICKUP = "pending pickup"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Order(BaseModel):
    id: str
    item_id: str
    volunteer_id: str
    placed_at: datetime
    order_status: OrderStatus

    class Config:
        from_attributes = True


class CreateOrderRequest(BaseModel):
    item_id: str


class UpdateOrderRequest(BaseModel):
    order_status: OrderStatus
