from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.models.user import user_model
from app.schemas.location import Location
from app.schemas.organization import (
    CreateOrganizationRequest,
    Organization,
    OrganizationStatus,
    UpdateOrganizationRequest,
)


class OrganizationModel:
    _instance: "OrganizationModel" = None

    def __init__(self):
        if OrganizationModel._instance is not None:
            raise Exception("This class is a singleton!")
        self.collection: AsyncIOMotorCollection = db["organizations"]

    @classmethod
    def get_instance(cls) -> "OrganizationModel":
        if OrganizationModel._instance is None:
            OrganizationModel._instance = cls()
        return OrganizationModel._instance

    async def create_indexes(self):
        try:
            await self.collection.create_index([("location", "2dsphere")])
        except Exception:
            pass

    async def get_all_organizations(
        self,
        lat: float | None = None,
        lng: float | None = None,
        distance_km: float | None = None,
    ) -> list[Organization]:
        filters = {"status": OrganizationStatus.APPROVED}
        if lat and lng and distance_km:
            location = Location(type="Point", coordinates=[lng, lat])
            distance = int(distance_km * 1000)
            filters["location"] = {
                "$near": {"$geometry": location.model_dump(), "$maxDistance": distance}
            }
        orgs_list = await self.collection.find(filters).to_list(length=None)

        return [Organization(**org) for org in orgs_list]

    async def get_organization_by_id(self, id: str) -> Organization:
        org = await self.collection.find_one(
            {"_id": ObjectId(id), "status": OrganizationStatus.APPROVED}
        )

        if not org:
            raise HTTPException(
                status_code=404, detail="Organization not found or it is not approved"
            )
        if org:
            return Organization(**org)
        return None

    async def create_organization(
        self, organization: CreateOrganizationRequest, user_id: str, location: Location
    ) -> Organization:
        org_data = organization.model_dump()
        org_data["status"] = OrganizationStatus.IN_REVIEW
        org_data["location"] = location.model_dump()

        result = await self.collection.insert_one(org_data)

        await user_model.update_entity_id_by_id(user_id, str(result.inserted_id))

        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})

        return Organization(**inserted_doc)

    async def update_organization(
        self, org_id: str, organization: UpdateOrganizationRequest, location: Location | None = None
    ) -> Organization:
        org_data = organization.model_dump(exclude_unset=True)
        if location:
            org_data["location"] = location.model_dump()
        await self.collection.update_one({"_id": ObjectId(org_id)}, {"$set": org_data})

        updated_doc = await self.collection.find_one({"_id": ObjectId(org_id)})
        return Organization(**updated_doc)

    async def delete_organization(self, id: str) -> None:
        await self.collection.update_one(
            {"_id": ObjectId(id)}, {"$set": {"status": OrganizationStatus.DELETED}}
        )


org_model = OrganizationModel.get_instance()
