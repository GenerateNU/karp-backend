from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.schemas.item import CreateItemRequest, Item, UpdateItemRequest
from app.utils.object_id import parse_object_id


class ItemModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["items"]

    async def create_item(self, item: CreateItemRequest, vendor_id: str) -> Item:
        item_data = item.model_dump()

        item_data["time_posted"] = datetime.now()
        item_data["vendor_id"] = ObjectId(vendor_id)
        item_data["status"] = "active"
        item_data["price"] = 30  # set to default 30 for now

        result = await self.collection.insert_one(item_data)
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})

        return self.to_item(inserted_doc)

    async def get_all_items(self) -> list[Item]:
        items_list = await self.collection.find().to_list(length=None)

        return [self.to_item(item) for item in items_list]

    async def get_item(self, item_id: str) -> Item | None:
        item_obj_id = parse_object_id(item_id)

        item = await self.collection.find_one({"_id": item_obj_id})

        if item is None:
            raise HTTPException(status_code=404, detail="Item does not exist!")

        return self.to_item(item)

    async def deactivate_item(self, item_id: str) -> None:
        item_obj_id = parse_object_id(item_id)

        result = await self.collection.update_one(
            {"_id": item_obj_id}, {"$set": {"status": "inactive"}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")

    async def activate_item(self, item_id: str) -> None:
        item_obj_id = parse_object_id(item_id)

        result = await self.collection.update_one(
            {"_id": item_obj_id}, {"$set": {"status": "active"}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")

    async def update_item(self, updated_item: UpdateItemRequest, item_id: str) -> None:
        item_obj_id = parse_object_id(item_id)

        # excludes updating fields not provided
        updated_data = updated_item.model_dump(exclude_unset=True)

        result = await db["items"].update_one({"_id": item_obj_id}, {"$set": updated_data})

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")

    # converting id and vendor_id to str to display all item fields
    def to_item(self, doc) -> Item:
        item_data = doc.copy()
        item_data["id"] = str(item_data["_id"])
        item_data["vendor_id"] = str(item_data["vendor_id"])
        return Item(**item_data)


item_model = ItemModel()
