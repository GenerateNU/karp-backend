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

        return [self._to_organization(org) for org in orgs_list]

    async def get_organization_by_id(self, id: str) -> Organization | None:
        org = await self.collection.find_one({"_id": ObjectId(id), "status": Status.APPROVED})

        if org:
            return self._to_organization(org)
        return None

    async def create_organization(
        self, organization: CreateOrganizationRequest, user_id: str
    ) -> Organization:
        org_data = organization.model_dump()
        org_data["status"] = Status.IN_REVIEW

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
        await self.collection.update_one(
            {"_id": ObjectId(id)}, {"$set": {"status": Status.DELETED}}
        )

    async def get_top_organizations(self, volunteer_id: str, limit: int) -> list[Organization]:
        pipeline = [
            {"$match": {"_id": volunteer_id}},
            # Get all completed registrations for volunteer
            {
                "$lookup": {
                    "from": "registrations",
                    "localField": "_id",
                    "foreignField": "volunteer_id",
                    "as": "registrations",
                }
            },
            {"$unwind": "$registrations"},
            {"$match": {"registrations.registration_status": "COMPLETED"}},
            # Get events from those registrations
            {
                "$lookup": {
                    "from": "event",
                    "localField": "event_id",
                    "foreignField": "_id",
                    "as": "event",
                }
            },
            {"$unwind": "$event"},
            # Calculate duration for each event and group by organization
            {
                "$addFields": {
                    "duration_ms": {"$subtract": ["$event.end_date_time", "$event.start_date_time"]}
                }
            },
            {
                "$group": {
                    "_id": "$event.organization_id",
                    "total_duration_ms": {"$sum": "$duration_ms"},
                }
            },
            {"$sort": {"total_duration_ms": -1}},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "organizations",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "organization",
                }
            },
            {"$unwind": "$organization"},
            {"$replaceRoot": {"newRoot": "$organization"}},
        ]
        results = await self.collection.aggregate(pipeline).to_list()

        return [org_model._to_organization(doc) for doc in results]

    def _to_organization(self, doc) -> Organization:
        org_data = doc.copy()
        org_data["id"] = str(org_data["_id"])
        return Organization(**org_data)


org_model = OrganizationModel()
