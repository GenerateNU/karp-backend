from typing import Literal

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.models.user import user_model
from app.schemas.location import Location
from app.schemas.organization import (
    CreateOrganizationRequest,
    Organization,
    Status,
    UpdateOrganizationRequest,
)


class OrganizationModel:
    _instance: "OrganizationModel" = None

    def __init__(self):
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
        filters = {"status": Status.APPROVED}
        if lat and lng and distance_km:
            location = Location(type="Point", coordinates=[lng, lat])
            distance = int(distance_km * 1000)
            filters["location"] = {
                "$near": {"$geometry": location.model_dump(), "$maxDistance": distance}
            }
        orgs_list = await self.collection.find(filters).to_list(length=None)

        return [Organization(**org) for org in orgs_list]

    async def get_organization_by_id(self, id: str) -> Organization:
        org = await self.collection.find_one({"_id": ObjectId(id), "status": Status.APPROVED})

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
        org_data["status"] = Status.IN_REVIEW
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
            {"_id": ObjectId(id)}, {"$set": {"status": Status.DELETED}}
        )

    async def search_organizations(
        self,
        q: str | None = None,
        sort_by: Literal["name", "status", "distance"] = "name",
        sort_dir: Literal["asc", "desc"] = "asc",
        statuses: list[Status] | None = None,
        lat: float | None = None,
        lng: float | None = None,
        distance_km: float | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[Organization]:
        filters: dict | None = None
        if statuses:
            filters_status = {"status": {"$in": list(statuses)}}
        elif sort_by == "status":
            filters_status = None
        else:
            filters_status = {"status": Status.APPROVED}

        filters = filters_status

        if q:
            filters_q = {
                "$or": [
                    {"name": {"$regex": q, "$options": "i"}},
                    {"description": {"$regex": q, "$options": "i"}},
                ]
            }
            filters = {"$and": [filters, filters_q]} if filters else filters_q

        use_geo = False
        if lat is not None and lng is not None and distance_km is not None:
            location = Location(type="Point", coordinates=[lng, lat])
            max_distance_meters = int(distance_km * 1000)
            geo_clause = {
                "location": {
                    "$near": {
                        "$geometry": location.model_dump(),
                        "$maxDistance": max_distance_meters,
                    }
                }
            }
            filters = {"$and": [filters, geo_clause]} if filters else geo_clause
            use_geo = True

        direction = 1 if sort_dir == "asc" else -1
        skip = max(0, (page - 1) * max(1, limit))
        safe_limit = max(1, min(200, limit))

        if sort_by == "status":
            match_stage = filters or {}
            status_order = {
                "APPROVED": 0,
                "IN_REVIEW": 1,
                "REJECTED": 2,
                "DELETED": 3,
            }

            status_branches = [
                {"case": {"$eq": ["$status", status]}, "then": rank}
                for status, rank in status_order.items()
            ]

            pipeline: list[dict] = []
            if match_stage:
                pipeline.append({"$match": match_stage})

            pipeline.append(
                {
                    "$addFields": {
                        "status_rank": {"$switch": {"branches": status_branches, "default": 99}}
                    }
                }
            )

            pipeline.append({"$sort": {"status_rank": direction, "_id": 1}})
            pipeline.append({"$project": {"status_rank": 0}})
            pipeline.append({"$skip": skip})
            pipeline.append({"$limit": safe_limit})

            docs = await self.collection.aggregate(pipeline).to_list(length=None)
            return [Organization(**d) for d in docs]

        elif sort_by == "distance" and use_geo:
            cursor = self.collection.find(filters or {}).skip(skip).limit(safe_limit)

        else:
            sort_field = sort_by if sort_by in ("name", "status") else "name"
            cursor = (
                self.collection.find(filters or {})
                .sort([(sort_field, direction), ("_id", 1)])
                .skip(skip)
                .limit(safe_limit)
            )

        docs = await cursor.to_list(length=None)
        return [Organization(**d) for d in docs]


org_model = OrganizationModel.get_instance()
