from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.models.user import user_model
from app.schemas.admin import (
    Admin,
)


class AdminModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["admins"]

    async def create_admin(self, admin_id: str) -> Admin:
        admin_data = {"is_active": True}
        result = await self.collection.insert_one(admin_data)
        print(admin_id)
        print(result.inserted_id)
        await user_model.update_entity_id_by_id(admin_id, str(result.inserted_id))
        pipeline = [
            {"$addFields": {"_id_str": {"$toString": "$_id"}}},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "_id_str",
                    "foreignField": "entity_id",
                    "as": "user",
                }
            },
            {"$unwind": "$user"},
            {
                "$match": {"user.entity_id": str(result.inserted_id)}
            },  # match by email in joined user document
        ]
        admin_data = await self.collection.aggregate(pipeline).to_list(length=1)
        if admin_data:
            return self.to_admin(admin_data[0])
        raise ValueError("No admin was able to be created")

    async def get_admin_by_id(self, admin_id: str) -> Admin | None:

        pipeline = [
            {"$match": {"_id": ObjectId(admin_id)}},
            {"$addFields": {"_id_str": {"$toString": "$_id"}}},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "_id_str",
                    "foreignField": "entity_id",  # or entity_id depending on your schema
                    "as": "user",
                }
            },
            {"$unwind": "$user"},
        ]
        admin_data = await self.collection.aggregate(pipeline).to_list(length=1)
        if admin_data:
            return self.to_admin(admin_data[0])

        raise ValueError("No admin with this ID was found")

    async def get_admin_by_email(self, email: str) -> Admin | None:

        pipeline = [
            {"$addFields": {"_id_str": {"$toString": "$_id"}}},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "_id_str",
                    "foreignField": "entity_id",
                    "as": "user",
                }
            },
            {"$unwind": "$user"},
            {"$match": {"user.email": email}},  # match by email in joined user document
        ]

        admin_data = await self.collection.aggregate(pipeline).to_list(length=1)

        if admin_data:
            print("email was found!")
            return self.to_admin(admin_data[0])

        raise ValueError("No admin with this email was found")

    async def get_all_admins(self) -> list[Admin]:
        pipeline = [
            # temp fix because entity_id is a string for some reason
            {"$addFields": {"_id_str": {"$toString": "$_id"}}},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "_id_str",
                    "foreignField": "entity_id",
                    "as": "user",
                }
            },
            {"$unwind": "$user"},
            {"$match": {"user.user_type": "ADMIN"}},
        ]
        admin_data = await self.collection.aggregate(pipeline).to_list()
        return [self.to_admin(admin) for admin in admin_data]

    # async def update_org_application_status(self, admin_id:
    # str, org_id: str, status: str) -> None:
    #     update_request = UpdateOrganizationRequest(status=status)
    #     await org_model.update_organization(org_id, update_request)

    # async def update_vendor_application_status(
    #     self, admin_id: str, vendor_id: str, status: str
    # ) -> None:
    #     update_request = UpdateVendorRequest(status=status)
    #     await org_model.update_vendor(vendor_id, update_request)

    async def delete_admin(self, admin_id: str) -> None:
        await self.collection.update_one(
            {"_id": ObjectId(admin_id)}, {"$set": {"is_active": False}}
        )

    def to_admin(self, doc) -> Admin:
        admin_data = doc.copy()
        # admin_data["id"] = str(admin_data["_id"])
        user_data = admin_data.get("user", {})
        return Admin(
            id=user_data.get("id"),
            email=user_data.get("email"),
            username=user_data.get("username"),
            hashed_password=user_data.get("hashed_password"),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            user_type=user_data.get("user_type"),
            entity_id=user_data.get("entity_id"),
            is_active=admin_data.get("is_active", True),
        )


admin_model = AdminModel()
