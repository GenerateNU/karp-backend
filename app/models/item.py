from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.core.enums import SortOrder
from app.database.mongodb import db
from app.schemas.item import CreateItemRequest, Item, ItemSortParam, Status, UpdateItemRequest
from app.utils.object_id import parse_object_id


class ItemModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["items"]

    async def create_item(self, item: CreateItemRequest, vendor_id: str) -> Item:
        item_data = item.model_dump()

        item_data["time_posted"] = datetime.now()
        item_data["vendor_id"] = ObjectId(vendor_id)
        item_data["status"] = Status.ACTIVE
        item_data["price"] = 30  # set to default 30 for now

        result = await self.collection.insert_one(item_data)
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})

        return Item(**inserted_doc)

    async def get_all_items(self) -> list[Item]:
        items_list = await self.collection.find().to_list(length=None)

        return [Item(**item) for item in items_list]

    async def get_items(
        self,
        search_text: str | None = None,
        vendor_id: str | None = None,
        sort_by: ItemSortParam | None = None,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> list[Item]:
        query = {}

        if search_text:
            query["name"] = {
                "$regex": search_text,
                "$options": "i",
            }  # case-insensitive partial match

        if vendor_id:
            query["vendor_id"] = ObjectId(vendor_id)

        sort_criteria = []
        if sort_by:
            sort_direction = 1 if sort_order == SortOrder.ASC else -1
            sort_criteria.append((sort_by.field_name, sort_direction))

        if sort_criteria:
            items_list = await self.collection.find(query).sort(sort_criteria).to_list()
        else:
            items_list = await self.collection.find(query).to_list()

        return [Item(**item) for item in items_list]

    async def get_item(self, item_id: str) -> Item | None:
        item_obj_id = parse_object_id(item_id)

        item = await self.collection.find_one({"_id": item_obj_id})

        if item is None:
            raise HTTPException(status_code=404, detail="Item does not exist!")

        return Item(**item)

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


item_model = ItemModel()
