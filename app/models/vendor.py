from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.schemas.vendor import CreateVendorRequest, Vendor


class VendorModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["vendors"]

    async def create_vendor(self, vendor: CreateVendorRequest) -> Vendor:
        vendor_data = vendor.model_dump()
        await self.collection.insert_one(vendor_data)
        return Vendor(**vendor_data)

    async def get_all_vendors(self) -> list[Vendor]:
        vendors_list = await self.collection.find().to_list(length=None)
        return [Vendor(**v) for v in vendors_list]

    async def approve_vendor(self, vendor_id: str) -> None:
        await self.collection.update_one({"_id": vendor_id}, {"$set": {"approved": True}})

    async def delete_all_vendors(self) -> None:
        await self.collection.delete_many({})


vendor_model = VendorModel()
