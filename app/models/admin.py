from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.schemas.admin import (
    Admin,
    OrgApplicationID,
    VendorApplicationID,
)


class AdminModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["admins"]

    async def create_admin(self, admin_data: dict, admin_id: str) -> Admin:
        result = await self.collection.insert_one(admin_data)
        admin_data["_id"] = result.inserted_id
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})
        return self.to_admin(inserted_doc)

    async def get_admin_by_id(self, admin_id: str) -> Admin | None:
        admin_data = await self.collection.find_one({"_id": ObjectId(admin_id)})
        if admin_data:
            return self.to_admin(admin_data)

        raise ValueError("No admin with this ID was found")

    async def get_admin_by_email(self, email: str) -> Admin | None:
        admin_data = await self.collection.find_one({"email": email})
        if admin_data:
            return self.to_admin(admin_data)

        raise ValueError("No admin with this email was found")

    async def get_all_admins(self) -> list[Admin]:
        admin_data = await self.collection.find().to_list(length=None)
        return [self.to_admin(admin) for admin in admin_data]

    async def add_org_application(self, admin_id: str, org_application: OrgApplicationID) -> None:
        await self.collection.update_one(
            {"_id": ObjectId(admin_id)},
            {"$push": {"org_applications": org_application.model_dump()}},
        )

    async def add_vendor_application(
        self, admin_id: str, vendor_application: VendorApplicationID
    ) -> None:
        await self.collection.update_one(
            {"_id": ObjectId(admin_id)},
            {"$push": {"vendor_applications": vendor_application.model_dump()}},
        )

    async def update_org_application_status(self, admin_id: str, org_id: str, status: str) -> None:
        await self.collection.update_one(
            {"_id": ObjectId(admin_id), "org_applications.organization_id": org_id},
            {"$set": {"org_applications.$.status": status}},
        )

    async def update_vendor_application_status(
        self, admin_id: str, vendor_id: str, status: str
    ) -> None:
        await self.collection.update_one(
            {"_id": ObjectId(admin_id), "vendor_applications.vendor_id": vendor_id},
            {"$set": {"vendor_applications.$.status": status}},
        )

    async def delete_admin(self, admin_id: str) -> None:
        await self.collection.update_one(
            {"_id": ObjectId(admin_id)}, {"$set": {"is_active": False}}
        )

    def to_admin(self, doc) -> Admin:
        admin_data = doc.copy()
        admin_data["id"] = str(admin_data["_id"])
        return Admin(**admin_data)


admin_model = AdminModel()
