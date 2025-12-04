from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.models.user import user_model
from app.schemas.location import Location
from app.schemas.vendor import CreateVendorRequest, UpdateVendorRequest, Vendor, VendorStatus


class VendorModel:
    _instance: "VendorModel" = None

    def __init__(self):
        if VendorModel._instance is not None:
            raise Exception("This class is a singleton!")
        self.collection: AsyncIOMotorCollection = db["vendors"]

    async def create_indexes(self):
        try:
            await self.collection.create_index([("location", "2dsphere")])
        except Exception:
            pass

    @classmethod
    def get_instance(cls) -> "VendorModel":
        if VendorModel._instance is None:
            VendorModel._instance = cls()
        return VendorModel._instance

    async def get_vendor_by_id(self, vendor_id: str) -> Vendor:
        vendor_data = await self.collection.find_one({"_id": ObjectId(vendor_id)})
        if not vendor_data:
            raise HTTPException(status_code=404, detail="Vendor is not found or it is not approved")
        if vendor_data:
            vendor = Vendor(**vendor_data)
            if vendor.location:
                print(
                    f"[VendorModel] Vendor {vendor_id} has location: "
                    f"{vendor.location.model_dump()}"
                )
            else:
                print(f"[VendorModel] WARNING: Vendor {vendor_id} has NO location")
            return vendor
        return None

    async def create_vendor(
        self, vendor: CreateVendorRequest, user_id: str, location: Location | None = None
    ) -> Vendor:
        vendor_data = vendor.model_dump(exclude={"address"})
        if location:
            vendor_data["location"] = location.model_dump()
        result = await self.collection.insert_one(vendor_data)

        await user_model.update_entity_id_by_id(user_id, str(result.inserted_id))

        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})
        return Vendor(**inserted_doc)

    async def get_all_vendors(
        self,
        status: VendorStatus | None = None,
        lat: float | None = None,
        lng: float | None = None,
        distance_km: float | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[Vendor]:
        filters: dict = {}
        if status:
            filters["status"] = status
        else:
            filters["status"] = VendorStatus.APPROVED

        # Filter by location using $geoNear in aggregation pipeline
        use_geo = lat is not None and lng is not None and distance_km is not None

        skip = max(0, (page - 1) * max(1, limit))
        safe_limit = max(1, min(200, limit))

        if use_geo:
            location = Location(type="Point", coordinates=[lng, lat])
            max_distance_meters = int(distance_km * 1000)

            # Build aggregation pipeline
            pipeline = []

            # Stage 1: $geoNear must be first in pipeline
            geo_near_stage = {
                "$geoNear": {
                    "near": location.model_dump(),
                    "distanceField": "distance",
                    "maxDistance": max_distance_meters,
                    "spherical": True,
                    "query": filters or {},  # Apply other filters in geoNear
                }
            }
            pipeline.append(geo_near_stage)

            # Stage 2: Skip and limit
            pipeline.append({"$skip": skip})
            pipeline.append({"$limit": safe_limit})

            # Execute aggregation
            vendors_list = await self.collection.aggregate(pipeline).to_list(length=None)
        else:
            # No location filter - use regular find
            vendors_list = (
                await self.collection.find(filters)
                .skip(skip)
                .limit(safe_limit)
                .to_list(length=None)
            )

        return [Vendor(**v) for v in vendors_list]

    async def update_vendor(
        self, vendor_id: str, vendor: UpdateVendorRequest, location: Location | None = None
    ) -> Vendor:
        vendor_data = vendor.model_dump(exclude_unset=True, exclude={"address"})
        location_updated = False
        if location:
            vendor_data["location"] = location.model_dump()
            location_updated = True

        await self.collection.update_one({"_id": ObjectId(vendor_id)}, {"$set": vendor_data})

        # If location was updated, sync it to all items from this vendor
        if location_updated:
            from app.models.item import item_model

            await item_model.collection.update_many(
                {"vendor_id": ObjectId(vendor_id)},
                {"$set": {"location": location.model_dump()}},
            )

        updated_doc = await self.collection.find_one({"_id": ObjectId(vendor_id)})
        return Vendor(**updated_doc)

    async def approve_vendor(self, vendor_id: str) -> None:
        await self.collection.update_one(
            {"_id": vendor_id}, {"$set": {"status": VendorStatus.APPROVED}}
        )

    async def delete_all_vendors(self) -> None:
        await self.collection.delete_many({})


vendor_model = VendorModel.get_instance()
