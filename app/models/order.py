from datetime import datetime
from typing import TYPE_CHECKING

from bson import ObjectId
from fastapi import HTTPException, status

from app.database.mongodb import db
from app.schemas.order import CreateOrderRequest, Order, OrderStatus, UpdateOrderRequest

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection


class OrderModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["orders"]

    async def get_order_by_id(self, order_id: str) -> Order:
        order = await self.collection.find_one({"_id": ObjectId(order_id)})
        return self._to_order(order) if order else None

    async def get_all_orders(self) -> list[Order]:
        orders_list = await self.collection.find().to_list(length=None)
        return [self._to_order(order) for order in orders_list]

    async def get_orders_by_item_id(self, item_id: str) -> list[Order]:
        orders_list = await self.collection.find({"item_id": ObjectId(item_id)}).to_list(
            length=None
        )
        return [self._to_order(order) for order in orders_list]

    async def get_orders_by_volunteer_id(self, volunteer_id: str) -> list[Order]:
        orders_list = await self.collection.find({"volunteer_id": ObjectId(volunteer_id)}).to_list(
            length=None
        )
        return [self._to_order(order) for order in orders_list]

    async def create_order(self, order: CreateOrderRequest, volunteer_id: str) -> Order:
        order_data = {
            "item_id": ObjectId(order.item_id),
            "volunteer_id": ObjectId(volunteer_id),
            "placed_at": datetime.now(),
            "order_status": OrderStatus.PENDING_PICKUP,
        }

        result = await self.collection.insert_one(order_data)
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})

        return self._to_order(inserted_doc)

    async def update_order_status(self, order_id: str, order_update: UpdateOrderRequest) -> Order:
        update_data = order_update.model_dump(exclude_unset=True)
        result = await self.collection.update_one(
            {"_id": ObjectId(order_id)}, {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        updated_doc = await self.collection.find_one({"_id": ObjectId(order_id)})
        return self._to_order(updated_doc)

    async def cancel_order(self, order_id: str) -> Order:
        result = await self.collection.update_one(
            {"_id": ObjectId(order_id)}, {"$set": {"order_status": OrderStatus.CANCELLED}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        updated_doc = await self.collection.find_one({"_id": ObjectId(order_id)})
        return self._to_order(updated_doc)

    def _to_order(self, doc) -> Order:
        order_data = doc.copy()
        order_data["id"] = str(order_data["_id"])
        order_data["item_id"] = str(order_data["item_id"])
        order_data["volunteer_id"] = str(order_data["volunteer_id"])
        return Order(**order_data)


order_model = OrderModel()
