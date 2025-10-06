from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.models.user import user_model
from app.schemas.vendor import CreateVendorRequest, UpdateVendorRequest, Vendor


class VendorModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["vendors"]

    async def create_vendor(self, vendor: CreateVendorRequest, user_id: str) -> Vendor:
        vendor_data = vendor.model_dump()
        result = await self.collection.insert_one(Vendor(**vendor_data).model_dump())

        await user_model.update_entity_id_by_id(user_id, str(result.inserted_id))

        return Vendor(**vendor_data)

    async def get_all_vendors(self) -> list[Vendor]:
        vendors_list = await self.collection.find().to_list(length=None)
        return [Vendor(**v) for v in vendors_list]

    async def update_vendor(self, vendor_id: str, vendor: UpdateVendorRequest) -> Vendor:
        vendor_data = vendor.model_dump(exclude_unset=True)

        await self.collection.update_one({"_id": ObjectId(vendor_id)}, {"$set": vendor_data})

        updated_doc = await self.collection.find_one({"_id": ObjectId(vendor_id)})
        return self._to_vendor(updated_doc)

    async def approve_vendor(self, vendor_id: str) -> None:
        await self.collection.update_one({"_id": vendor_id}, {"$set": {"approved": True}})

    async def delete_all_vendors(self) -> None:
        await self.collection.delete_many({})

    def _to_vendor(self, doc) -> Vendor:
        vendor_data = doc.copy()
        vendor_data["id"] = str(vendor_data["_id"])
        return Vendor(**vendor_data)


vendor_model = VendorModel()
