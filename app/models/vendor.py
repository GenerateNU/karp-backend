from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.models.user import user_model
from app.schemas.vendor import CreateVendorRequest, UpdateVendorRequest, Vendor, VendorStatus


class VendorModel:
    _instance: "VendorModel" = None

    def __init__(self):
        if VendorModel._instance is not None:
            raise Exception("This class is a singleton!")
        self.collection: AsyncIOMotorCollection = db["vendors"]

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
            return Vendor(**vendor_data)
        return None

    async def create_vendor(self, vendor: CreateVendorRequest, user_id: str) -> Vendor:
        vendor_data = vendor.model_dump()
        result = await self.collection.insert_one(Vendor(**vendor_data).model_dump())

        await user_model.update_entity_id_by_id(user_id, str(result.inserted_id))

        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})
        return Vendor(**inserted_doc)

    async def get_all_vendors(self, status: VendorStatus | None = None) -> list[Vendor]:
        query: dict = {}
        if status:
            query["status"] = status
        vendors_list = await self.collection.find(query).to_list(length=None)
        return [Vendor(**v) for v in vendors_list]

    async def update_vendor(self, vendor_id: str, vendor: UpdateVendorRequest) -> Vendor:
        vendor_data = vendor.model_dump(exclude_unset=True)

        await self.collection.update_one({"_id": ObjectId(vendor_id)}, {"$set": vendor_data})

        updated_doc = await self.collection.find_one({"_id": ObjectId(vendor_id)})
        return Vendor(**updated_doc)

    async def approve_vendor(self, vendor_id: str) -> None:
        await self.collection.update_one({"_id": vendor_id}, {"$set": {"approved": True}})

    async def delete_all_vendors(self) -> None:
        await self.collection.delete_many({})


vendor_model = VendorModel.get_instance()
