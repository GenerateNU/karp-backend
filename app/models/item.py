from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.schemas.item import CreateItemRequest, Item, UpdateItemRequest


class ItemModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["items"]

    async def create_item(self, item: CreateItemRequest, vendor_id: str) -> Item:
        item_data = item.model_dump()

        item_data["timePosted"] = datetime.now()
        item_data["expiration"] = datetime.strptime(item_data["expiration"], "%d-%m-%Y")
        item_data["vendorId"] = ObjectId(vendor_id)
        item_data["status"] = "active"
        item_data["price"] = 30  # set to default 30 for now

        await self.collection.insert_one(item_data)

        return Item(**item_data)

    async def get_all_items(self) -> list[Item]:
        items_list = await self.collection.find().to_list(length=None)

        return [Item(**item) for item in items_list]

    async def get_item(self, item_id: str) -> Item | None:
        try:
            item_obj_id = ObjectId(item_id)
        except Exception as err:
            raise HTTPException(
                status_code=500, detail="Item id can't be converted to Object Id!"
            ) from err

        item = await self.collection.find_one({"_id": item_obj_id})

        if item is None:
            raise HTTPException(status_code=404, detail="Item does not exist!")

        return Item(**item)

    async def deactivate_item(self, item_id: str) -> None:
        try:
            item_obj_id = ObjectId(item_id)
        except Exception as err:
            raise HTTPException(
                status_code=500, detail="Item id can't be converted to Object Id!"
            ) from err

        result = await self.collection.update_one(
            {"_id": item_obj_id}, {"$set": {"status": "inactive"}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")

    async def activate_item(self, item_id: str) -> None:
        try:
            item_obj_id = ObjectId(item_id)
        except Exception as err:
            raise HTTPException(
                status_code=500, detail="Item id can't be converted to Object Id!"
            ) from err

        result = await self.collection.update_one(
            {"_id": item_obj_id}, {"$set": {"status": "active"}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")

    async def update_item(self, updated_item: UpdateItemRequest, item_id: str) -> None:
        try:
            item_obj_id = ObjectId(item_id)
        except Exception as err:
            raise HTTPException(
                status_code=500, detail="Item id can't be converted to Object Id!"
            ) from err
        # excludes updating fields not provided
        updated_data = updated_item.model_dump(exclude_unset=True)

        if "expiration" in updated_data:
            updated_data["expiration"] = datetime.strptime(updated_data["expiration"], "%d-%m-%Y")

        result = await db["items"].update_one({"_id": item_obj_id}, {"$set": updated_data})

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")


item_model = ItemModel()
