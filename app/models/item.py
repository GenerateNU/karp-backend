from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.core.enums import SortOrder
from app.database.mongodb import db
from app.schemas.item import CreateItemRequest, Item, ItemSortParam, ItemStatus, UpdateItemRequest
from app.schemas.location import Location
from app.utils.object_id import parse_object_id


class ItemModel:
    _instance: "ItemModel" = None

    def __init__(self):
        if ItemModel._instance is not None:
            raise Exception("This class is a singleton!")
        self.collection: AsyncIOMotorCollection = db["items"]

    @classmethod
    def get_instance(cls) -> "ItemModel":
        if ItemModel._instance is None:
            ItemModel._instance = cls()
        return ItemModel._instance

    async def create_item(self, item: CreateItemRequest, vendor_id: str) -> Item:
        item_data = item.model_dump()

        item_data["time_posted"] = datetime.now()
        item_data["vendor_id"] = ObjectId(vendor_id)
        item_data["status"] = ItemStatus.PUBLISHED
        item_data["price"] = int(item.dollar_price * 100)

        if "tags" not in item_data:
            item_data["tags"] = []

        result = await self.collection.insert_one(item_data)
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})

        return Item(**inserted_doc)

    async def get_all_items(self) -> list[Item]:
        items_list = await self.collection.find().to_list(length=None)

        return [Item(**item) for item in items_list]

    async def get_items(
        self,
        status: ItemStatus | None = None,
        search_text: str | None = None,
        vendor_id: str | None = None,
        sort_by: ItemSortParam | None = None,
        sort_order: SortOrder = SortOrder.ASC,
        lat: float | None = None,
        lng: float | None = None,
        distance_km: float | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[Item]:
        filters: dict = {}

        if status:
            filters["status"] = status
        else:
            filters["status"] = ItemStatus.ACTIVE

        if search_text:
            filters["name"] = {
                "$regex": search_text,
                "$options": "i",
            }  # case-insensitive partial match

        if vendor_id:
            filters["vendor_id"] = ObjectId(vendor_id)

        # Filter by location through vendor
        # First find vendors within the location radius, then filter items by those vendors
        vendor_ids = None
        if lat is not None and lng is not None and distance_km is not None:
            from app.models.vendor import vendor_model

            location = Location(type="Point", coordinates=[lng, lat])
            max_distance_meters = int(distance_km * 1000)

            # Use $geoNear in aggregation pipeline for vendor query
            vendor_pipeline = [
                {
                    "$geoNear": {
                        "near": location.model_dump(),
                        "distanceField": "distance",
                        "maxDistance": max_distance_meters,
                        "spherical": True,
                    }
                },
                {"$project": {"_id": 1}},
            ]
            vendors_list = await vendor_model.collection.aggregate(vendor_pipeline).to_list(
                length=None
            )
            vendor_ids = [ObjectId(v["_id"]) for v in vendors_list if v.get("_id")]

            if not vendor_ids:
                # No vendors in range, return empty list
                return []

            # Add vendor filter
            if "$and" in filters:
                filters["$and"].append({"vendor_id": {"$in": vendor_ids}})
            elif filters:
                filters = {"$and": [filters, {"vendor_id": {"$in": vendor_ids}}]}
            else:
                filters = {"vendor_id": {"$in": vendor_ids}}

        sort_criteria = []
        if sort_by:
            sort_direction = 1 if sort_order == SortOrder.ASC else -1
            sort_criteria.append((sort_by.field_name, sort_direction))

        skip = max(0, (page - 1) * max(1, limit))
        safe_limit = max(1, min(200, limit))

        if sort_criteria:
            items_list = (
                await self.collection.find(filters)
                .sort(sort_criteria)
                .skip(skip)
                .limit(safe_limit)
                .to_list()
            )
        else:
            items_list = await self.collection.find(filters).skip(skip).limit(safe_limit).to_list()

        return [Item(**item) for item in items_list]

    async def get_item_by_id(self, item_id: str) -> Item | None:
        item_obj_id = parse_object_id(item_id)

        item = await self.collection.find_one({"_id": item_obj_id})

        if item is None:
            raise HTTPException(status_code=404, detail="Item does not exist!")

        return Item(**item)

    async def deactivate_item(self, item_id: str) -> None:
        item_obj_id = parse_object_id(item_id)

        result = await self.collection.update_one(
            {"_id": item_obj_id}, {"$set": {"status": ItemStatus.PUBLISHED}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")

    async def activate_item(self, item_id: str) -> None:
        item_obj_id = parse_object_id(item_id)

        result = await self.collection.update_one(
            {"_id": item_obj_id}, {"$set": {"status": ItemStatus.ACTIVE}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")

    async def update_item(self, updated_item: UpdateItemRequest, item_id: str) -> None:
        item_obj_id = parse_object_id(item_id)

        # excludes updating fields not provided
        updated_data = updated_item.model_dump(exclude_unset=True)

        if "dollar_price" in updated_data:
            updated_data["price"] = int(updated_data["dollar_price"] * 100)
            del updated_data["dollar_price"]

        result = await db["items"].update_one({"_id": item_obj_id}, {"$set": updated_data})

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")

    async def update_item_image(self, item_id: str, s3_key: str) -> str:
        print(f"updating the item image: {s3_key}")
        updated_event = await self.collection.update_one(
            {"_id": ObjectId(item_id)}, {"$set": {"image_s3_key": s3_key}}
        )
        print(updated_event)
        print("sucessfully updated item image s3 key in mongo")
        return s3_key


item_model = ItemModel.get_instance()
