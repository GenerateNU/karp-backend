from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.models.user import user_model
from app.schemas.organization import (
    CreateOrganizationRequest,
    Organization,
    Status,
    UpdateOrganizationRequest,
)


class OrganizationModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["organizations"]

    async def get_all_organizations(self) -> list[Organization]:
        orgs_list = await self.collection.find({"status": Status.APPROVED}).to_list(length=None)

        return [Organization(**org) for org in orgs_list]

    async def get_organization_by_id(self, id: str) -> Organization | None:
        org = await self.collection.find_one({"_id": ObjectId(id), "status": Status.APPROVED})

        if org:
            return Organization(**org)
        return None

    async def create_organization(
        self, organization: CreateOrganizationRequest, user_id: str
    ) -> Organization:
        org_data = organization.model_dump()
        org_data["status"] = Status.IN_REVIEW

        result = await self.collection.insert_one(org_data)

        await user_model.update_entity_id_by_id(user_id, str(result.inserted_id))

        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})
        return Organization(**inserted_doc)

    async def update_organization(
        self, org_id: str, organization: UpdateOrganizationRequest
    ) -> Organization:
        org_data = organization.model_dump(exclude_unset=True)

        await self.collection.update_one({"_id": ObjectId(org_id)}, {"$set": org_data})

        updated_doc = await self.collection.find_one({"_id": ObjectId(org_id)})
        return Organization(**updated_doc)

    async def delete_organization(self, id: str) -> None:
        await self.collection.update_one(
            {"_id": ObjectId(id)}, {"$set": {"status": Status.DELETED}}
        )


org_model = OrganizationModel()
