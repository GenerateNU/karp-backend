from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.models.user import user_model
from app.schemas.organization import (
    CreateOrganizationRequest,
    Organization,
    UpdateOrganizationRequest,
)


class OrganizationModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["organizations"]

    async def get_all_organizations(self) -> list[Organization]:
        orgs_list = await self.collection.find({"isActive": True}).to_list(length=None)

        return [self._to_organization(org) for org in orgs_list]

    async def get_organization_by_id(self, id: str) -> Organization | None:
        org = await self.collection.find_one({"_id": ObjectId(id), "isActive": True})

        if org:
            return self._to_organization(org)
        return None

    async def create_organization(
        self, organization: CreateOrganizationRequest, user_id: str
    ) -> Organization:
        org_data = organization.model_dump()
        org_data["isActive"] = True

        result = await self.collection.insert_one(org_data)

        await user_model.update_entity_id_by_id(user_id, str(result.inserted_id))

        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})
        return self._to_organization(inserted_doc)

    async def update_organization(
        self, org_id: str, organization: UpdateOrganizationRequest
    ) -> Organization:
        org_data = organization.model_dump(exclude_unset=True)

        await self.collection.update_one({"_id": ObjectId(org_id)}, {"$set": org_data})

        updated_doc = await self.collection.find_one({"_id": ObjectId(org_id)})
        return self._to_organization(updated_doc)

    async def delete_organization(self, id: str) -> None:
        await self.collection.update_one({"_id": ObjectId(id)}, {"$set": {"isActive": False}})

    def _to_organization(self, doc) -> Organization:
        org_data = doc.copy()
        org_data["id"] = str(org_data["_id"])
        return Organization(**org_data)


org_model = OrganizationModel()
