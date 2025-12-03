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
        sort_by: Literal["name", "status", "distance"] = "name",
        sort_dir: Literal["asc", "desc"] = "asc",
        statuses: list[OrganizationStatus] | None = None,
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
            filters_status = {"status": OrganizationStatus.APPROVED}

        filters = filters_status

        use_geo = lat is not None and lng is not None and distance_km is not None

        direction = 1 if sort_dir == "asc" else -1
        skip = max(0, (page - 1) * max(1, limit))
        safe_limit = max(1, min(200, limit))

        if use_geo:
            location = Location(type="Point", coordinates=[lng, lat])
            max_distance_meters = int(distance_km * 1000)

            # Build aggregation pipeline for geospatial query
            pipeline = []

            # Stage 1: $geoNear must be first
            geo_near_stage = {
                "$geoNear": {
                    "near": location.model_dump(),
                    "distanceField": "distance",
                    "maxDistance": max_distance_meters,
                    "spherical": True,
                    "query": filters or {},
                }
            }
            pipeline.append(geo_near_stage)

            if sort_by == "status":
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
                pipeline.append(
                    {
                        "$addFields": {
                            "status_rank": {"$switch": {"branches": status_branches, "default": 99}}
                        }
                    }
                )
                pipeline.append({"$sort": {"status_rank": direction, "_id": 1}})
                pipeline.append({"$project": {"status_rank": 0}})
            elif sort_by == "distance":
                # Sort by distance (already calculated by $geoNear)
                pipeline.append({"$sort": {"distance": direction, "_id": 1}})
            else:
                # Sort by name
                pipeline.append({"$sort": {"name": direction, "_id": 1}})

            pipeline.append({"$skip": skip})
            pipeline.append({"$limit": safe_limit})

            docs = await self.collection.aggregate(pipeline).to_list(length=None)
            return [Organization(**d) for d in docs]

        else:
            # No location filter - use regular find
            if sort_by == "status":
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

                pipeline = []
                if filters:
                    pipeline.append({"$match": filters})
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
        org_data["status"] = OrganizationStatus.PENDING
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

    async def search_organizations(
        self,
        q: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        distance_km: float | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[Organization]:
        filters: dict = {}

        if q:
            filters = {
                "$or": [
                    {"name": {"$regex": q, "$options": "i"}},
                    {"description": {"$regex": q, "$options": "i"}},
                ]
            }

        # Filter by location using $geoNear in aggregation pipeline
        use_geo = lat is not None and lng is not None and distance_km is not None

        skip = max(0, (page - 1) * max(1, limit))
        safe_limit = max(1, min(200, limit))

        if use_geo:
            location = Location(type="Point", coordinates=[lng, lat])
            max_distance_meters = int(distance_km * 1000)

            # Build aggregation pipeline
            pipeline = []

            # Stage 1: $geoNear must be first in pipeline
            geo_near_stage = {
                "$geoNear": {
                    "near": location.model_dump(),
                    "distanceField": "distance",
                    "maxDistance": max_distance_meters,
                    "spherical": True,
                    "query": filters or {},  # Apply other filters in geoNear
                }
            }
            pipeline.append(geo_near_stage)

            # Stage 2: Sort
            pipeline.append({"$sort": {"name": 1, "_id": 1}})

            # Stage 3: Skip and limit
            pipeline.append({"$skip": skip})
            pipeline.append({"$limit": safe_limit})

            # Execute aggregation
            docs = await self.collection.aggregate(pipeline).to_list(length=None)
        else:
            # No location filter - use regular find
            cursor = (
                self.collection.find(filters or {})
                .sort([("name", 1), ("_id", 1)])
                .skip(skip)
                .limit(safe_limit)
            )
            docs = await cursor.to_list(length=None)

        return [Organization(**d) for d in docs]

    async def update_organization_image(self, org_id: str, s3_key: str) -> str:
        await self.collection.update_one(
            {"_id": ObjectId(org_id)}, {"$set": {"image_s3_key": s3_key}}
        )
        return s3_key


org_model = OrganizationModel.get_instance()
